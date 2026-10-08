import json
import os
import re
import socket
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from src.models.note import Note, db

note_bp = Blueprint('note', __name__)
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
TRANSLATION_TIMEOUT_SECONDS = 30
TARGET_LANGUAGES = {
    'zh-CN': 'Simplified Chinese',
    'en': 'English',
    'ja': 'Japanese',
}


def _safe_openrouter_error_detail(error):
    try:
        response_body = json.loads(error.read().decode('utf-8'))
        provider_error = response_body.get('error', {})
        detail = provider_error.get('message') if isinstance(provider_error, dict) else None
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError, OSError):
        return None

    if not isinstance(detail, str):
        return None
    detail = ' '.join(detail.split())
    detail = re.sub(r'(?i)\bBearer\s+\S+', 'Bearer [redacted]', detail)
    detail = re.sub(r'\bsk-(?:or-v1-)?[A-Za-z0-9_-]{16,}\b', '[redacted key]', detail, flags=re.IGNORECASE)
    detail = re.sub(r'(?i)(postgres(?:ql)?://)[^@\s]+@', r'\1[redacted]@', detail)
    return detail[:240] or None


@note_bp.route('/notes/translate', methods=['POST'])
def translate_note():
    """Translate a note without changing its saved contents."""
    data = request.get_json(silent=True) or {}
    title = data.get('title', '')
    content = data.get('content', '')
    target_language = data.get('target_language')

    if not isinstance(title, str) or not isinstance(content, str):
        return jsonify({'error': 'Title and content must be text.'}), 400
    if not title.strip() and not content.strip():
        return jsonify({'error': 'Enter a title or note content before translating.'}), 400
    if not isinstance(target_language, str) or target_language not in TARGET_LANGUAGES:
        return jsonify({'error': 'Choose Simplified Chinese, English, or Japanese.'}), 400

    api_key = os.getenv('OPENROUTER_API_KEY')
    model = os.getenv('OPENROUTER_MODEL')
    if not api_key:
        return jsonify({'error': 'Translation is not configured: OPENROUTER_API_KEY is missing.'}), 503
    if not model:
        return jsonify({'error': 'Translation is not configured: OPENROUTER_MODEL is missing.'}), 503

    prompt_path = Path(__file__).resolve().parents[2] / 'prompts' / 'translate_prompt.md'
    try:
        system_prompt = prompt_path.read_text(encoding='utf-8')
    except OSError:
        return jsonify({'error': 'Translation prompt file is unavailable on the server.'}), 500

    payload = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': f'{system_prompt}\n\nTarget language: {TARGET_LANGUAGES[target_language]}.',
            },
            {
                'role': 'user',
                'content': json.dumps({'title': title, 'content': content}, ensure_ascii=False),
            },
        ],
        'temperature': 0.2,
    }
    api_request = Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urlopen(api_request, timeout=TRANSLATION_TIMEOUT_SECONDS) as response:
            provider_response = json.loads(response.read().decode('utf-8'))
    except HTTPError as error:
        provider_detail = _safe_openrouter_error_detail(error)
        if error.code == 401 or error.code == 403:
            message = 'OpenRouter rejected the API key or model access. Check your server configuration.'
        elif error.code == 429:
            message = 'OpenRouter rate limit reached. Please try again shortly.'
        elif error.code == 402:
            message = provider_detail or 'OpenRouter requires available credits for this request. Check your account balance, usage limits, and model pricing.'
        else:
            message = f'OpenRouter request failed with HTTP {error.code}.'
        return jsonify({'error': message}), 502
    except (TimeoutError, socket.timeout):
        return jsonify({'error': 'Translation timed out. Please try again.'}), 504
    except URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return jsonify({'error': 'Translation timed out. Please try again.'}), 504
        return jsonify({'error': 'Could not connect to OpenRouter. Check the server network and try again.'}), 502
    except (UnicodeDecodeError, json.JSONDecodeError):
        return jsonify({'error': 'OpenRouter returned an unreadable response.'}), 502

    try:
        translated_text = provider_response['choices'][0]['message']['content']
        translated = json.loads(translated_text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return jsonify({'error': 'Translation result was not valid JSON with title and content fields.'}), 502

    if not isinstance(translated, dict):
        return jsonify({'error': 'Translation result must be a JSON object with title and content fields.'}), 502
    translated_title = translated.get('title')
    translated_content = translated.get('content')
    if not isinstance(translated_title, str) or not isinstance(translated_content, str):
        return jsonify({'error': 'Translation result must contain text fields named title and content.'}), 502
    if (title.strip() and not translated_title.strip()) or (content.strip() and not translated_content.strip()):
        return jsonify({'error': 'Translation result was missing translated title or content.'}), 502

    return jsonify({'title': translated_title.strip(), 'content': translated_content.strip()})

@note_bp.route('/notes', methods=['GET'])
def get_notes():
    """Get all notes, ordered by most recently updated"""
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])

@note_bp.route('/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    try:
        data = request.json
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400
        
        note = Note(title=data['title'], content=data['content'])
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        if isinstance(e, SQLAlchemyError):
            return jsonify({'error': 'Database operation failed. Check database configuration and connectivity.'}), 503
        return jsonify({'error': 'Could not create the note.'}), 500

@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())

@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        note.title = data.get('title', note.title)
        note.content = data.get('content', note.content)
        db.session.commit()
        return jsonify(note.to_dict())
    except Exception as e:
        db.session.rollback()
        if isinstance(e, SQLAlchemyError):
            return jsonify({'error': 'Database operation failed. Check database configuration and connectivity.'}), 503
        return jsonify({'error': 'Could not update the note.'}), 500

@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        if isinstance(e, SQLAlchemyError):
            return jsonify({'error': 'Database operation failed. Check database configuration and connectivity.'}), 503
        return jsonify({'error': 'Could not delete the note.'}), 500

@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    """Search notes by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    notes = Note.query.filter(
        (Note.title.contains(query)) | (Note.content.contains(query))
    ).order_by(Note.updated_at.desc()).all()
    
    return jsonify([note.to_dict() for note in notes])

