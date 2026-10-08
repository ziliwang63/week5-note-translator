import os
import secrets
import sys
from pathlib import Path

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import make_url
from sqlalchemy.exc import SQLAlchemyError
from click import ClickException, echo

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / '.env')

from src.models.user import db
from src.routes.user import user_bp
from src.routes.note import note_bp
from src.models.note import Note

IS_VERCEL = os.getenv('VERCEL') == '1'
APP_ENV = os.getenv('APP_ENV', '').strip().lower()
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
SECRET_KEY = os.getenv('SECRET_KEY')

if IS_VERCEL and not DATABASE_URL:
    raise RuntimeError('DATABASE_URL must be configured for Vercel deployments.')
if not SECRET_KEY:
    if not IS_VERCEL and APP_ENV in {'development', 'local'}:
        SECRET_KEY = secrets.token_hex(32)
    else:
        raise RuntimeError('SECRET_KEY must be configured outside local development.')

app = Flask(__name__, static_folder=None)
app.config['SECRET_KEY'] = SECRET_KEY


def build_database_uri(database_url, app_env):
    if not database_url:
        if app_env not in {'development', 'local'}:
            raise RuntimeError('DATABASE_URL is required outside local development.')
        db_path = ROOT_DIR / 'database' / 'app.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f'sqlite:///{db_path}'

    try:
        url = make_url(database_url)
    except Exception:
        raise RuntimeError('DATABASE_URL is invalid. Check its format and encoding.') from None

    if url.drivername in {'postgres', 'postgresql'}:
        url = url.set(drivername='postgresql+psycopg')
    elif url.drivername != 'postgresql+psycopg':
        raise RuntimeError('DATABASE_URL must use PostgreSQL with the psycopg driver.')

    query = dict(url.query)
    if not query.get('sslmode'):
        query['sslmode'] = os.getenv('DB_SSLMODE', 'require').strip() or 'require'
    return url.set(query=query)

# Enable CORS for all routes
CORS(app)

# register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(note_bp, url_prefix='/api')
app.config['SQLALCHEMY_DATABASE_URI'] = build_database_uri(
    DATABASE_URL, 'production' if IS_VERCEL else APP_ENV
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
db.init_app(app)


@app.cli.command('init-db')
def initialize_database():
    """Create any missing tables for the registered models."""
    try:
        with app.app_context():
            db.create_all()
    except SQLAlchemyError:
        app.logger.error('Database initialization failed; verify DATABASE_URL, credentials, SSL settings, and connectivity.')
        raise ClickException(
            'Database initialization failed. Check DATABASE_URL, credentials, SSL settings, and connectivity.'
        ) from None
    echo('Database tables are ready. Existing tables and data were not removed.')


@app.errorhandler(SQLAlchemyError)
def handle_database_error(_error):
    app.logger.error('Database operation failed; verify DATABASE_URL, credentials, SSL settings, and connectivity.')
    return jsonify({
        'error': 'Database operation failed. Check database configuration and connectivity.'
    }), 503

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    public_dir = ROOT_DIR / 'public'
    if path:
        requested_path = (public_dir / path).resolve()
        if public_dir.resolve() in requested_path.parents and requested_path.is_file():
            return send_from_directory(public_dir, path)
    index_path = public_dir / 'index.html'
    if index_path.is_file():
        return send_from_directory(public_dir, 'index.html')
    return 'index.html not found', 404


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', '5001')),
        debug=not IS_VERCEL and APP_ENV in {'development', 'local'},
    )
