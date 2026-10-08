# NoteTaker - Personal Note Management Application

A modern, responsive web application for managing personal notes with a beautiful user interface and full CRUD functionality.

## 🌟 Features

- **Create Notes**: Add new notes with titles and rich content
- **Edit Notes**: Update existing notes with real-time editing
- **Delete Notes**: Remove notes you no longer need
- **Search Notes**: Find notes quickly by searching titles and content
- **Translate Notes**: Preview title and content translations in Simplified Chinese, English, or Japanese before applying them
- **Auto-save**: Notes are automatically saved as you type
- **Responsive Design**: Works perfectly on desktop and mobile devices
- **Modern UI**: Beautiful gradient design with smooth animations
- **Real-time Updates**: Instant feedback and updates

## 🚀 Live Demo

The application is deployed and accessible at: **https://3dhkilc88dkk.manus.space**

## 🛠 Technology Stack

### Frontend
- **HTML5**: Semantic markup structure
- **CSS3**: Modern styling with gradients, animations, and responsive design
- **JavaScript (ES6+)**: Interactive functionality and API communication

### Backend
- **Python Flask**: Web framework for API endpoints
- **SQLAlchemy**: ORM for database operations
- **Flask-CORS**: Cross-origin resource sharing support

### Database
- **Neon PostgreSQL**: Used when `DATABASE_URL` is configured
- **SQLite**: Local development fallback only

## 📁 Project Structure

```
notetaking-app/
├── src/
│   ├── models/
│   │   ├── user.py          # User model (template)
│   │   └── note.py          # Note model with database schema
│   ├── routes/
│   │   ├── user.py          # User API routes (template)
│   │   └── note.py          # Note API endpoints
│   └── main.py              # Flask application entry point
├── public/
│   └── index.html            # Frontend served by Vercel CDN
├── .venv/                   # Python virtual environment
├── prompts/                 # LLM prompts
├── vercel.json              # Vercel Function configuration
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🔧 Local Development Setup

### Prerequisites
- Python 3.11+
- pip (Python package manager)

### Installation Steps

1. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   If you do not already have a local `.env`, create one with:
   ```bash
   cp .env.example .env
   ```
   Keep `.env` out of Git.

   For Neon, set `APP_ENV=production`, a strong `SECRET_KEY`, and paste the connection string from Neon into `DATABASE_URL`. Use the provider's PostgreSQL URL; the app accepts `postgres://` or `postgresql://`, selects psycopg 3, and defaults to `sslmode=require` when the URL has no `sslmode` parameter. Existing SSL parameters are preserved. `DB_SSLMODE` can override the default.

   For local-only development without Neon, set `APP_ENV=development` and leave `DATABASE_URL` empty. This is the only mode that creates/uses `database/app.db`.

   Configure `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` for note translation as needed.

4. **Initialize database tables**
   Run this once after configuring the Neon URL:
   ```bash
   .venv/bin/flask --app src.main init-db
   ```

   The command creates any missing tables for the existing SQLAlchemy models (`User` and `Note`) and does not drop tables or delete rows. A newly provisioned Neon database will initially contain no notes. Existing notes in local SQLite are not migrated automatically.

5. **Start the application**
   ```bash
   .venv/bin/python src/main.py
   ```

6. **Access the application**
   - Open your browser and go to `http://localhost:5001`

## 📡 API Endpoints

### Notes API
- `GET /api/notes` - Get all notes
- `POST /api/notes` - Create a new note
- `GET /api/notes/<id>` - Get a specific note
- `PUT /api/notes/<id>` - Update a note
- `DELETE /api/notes/<id>` - Delete a note
- `GET /api/notes/search?q=<query>` - Search notes
- `POST /api/notes/translate` - Translate a note without saving it

Translation request body:
```json
{
   "title": "Meeting notes",
   "content": "Discuss the next release.",
   "target_language": "ja"
}
```

### Request/Response Format
```json
{
  "id": 1,
  "title": "My Note Title",
  "content": "Note content here...",
  "created_at": "2025-09-03T11:26:38.123456",
  "updated_at": "2025-09-03T11:27:30.654321"
}
```

## 🎨 User Interface Features

### Sidebar
- **Search Box**: Real-time search through note titles and content
- **New Note Button**: Create new notes instantly
- **Notes List**: Scrollable list of all notes with previews
- **Note Previews**: Show title, content preview, and last modified date

### Editor Panel
- **Title Input**: Edit note titles
- **Content Textarea**: Rich text editing area
- **Save Button**: Manual save option (auto-save also available)
- **Delete Button**: Remove notes with confirmation
- **Real-time Updates**: Changes reflected immediately

### Design Elements
- **Gradient Background**: Beautiful purple gradient backdrop
- **Glass Morphism**: Semi-transparent panels with backdrop blur
- **Smooth Animations**: Hover effects and transitions
- **Responsive Layout**: Adapts to different screen sizes
- **Modern Typography**: Clean, readable font stack

## 🔒 Database Schema

### Notes Table
```sql
CREATE TABLE note (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🚀 Vercel Deployment

Vercel's Flask runtime recognizes the exported `app` in `src/main.py`. Importing this module does not start the local development server. Static files are in the root `public/` directory and served by Vercel's CDN; Flask's `static_folder` is disabled. The frontend calls same-origin `/api/...` paths, which Vercel routes to the Flask Function.

Configure the Vercel project as follows:
- **Root Directory**: repository root (`.`), containing `requirements.txt` and `vercel.json`
- **Framework Preset**: Flask; if Flask is not offered by the dashboard, select Other and keep automatic Python runtime detection enabled
- **Build Command**: leave blank (the Flask deployment is zero-configuration)
- **Output Directory**: leave blank; Vercel serves `public/` and deploys the Python Function

Set these environment variables in Vercel for Production, and for Preview if preview deployments need database access:
- `DATABASE_URL`: Neon PostgreSQL connection URL (required; Vercel never uses SQLite)
- `SECRET_KEY`: strong, random Flask secret
- `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`: required for translation
- `APP_ENV`: `production` (debug mode remains off on Vercel in all cases)
- `DB_SSLMODE`: optional; defaults to `require` unless `DATABASE_URL` has an SSL mode

Before first use, initialize the Neon schema once by running `.venv/bin/flask --app src.main init-db` in an environment configured with the same `DATABASE_URL`. This creates missing model tables only; it does not remove or migrate existing data. A new Neon database starts with no notes. Do not run this command as a Vercel build step.

`vercel.json` configures the `src/main.py` Function, a 60-second maximum duration, and bundles `prompts/**` and `public/**` so `prompts/translate_prompt.md` is available at runtime.

Official guidance: [Deploy a Flask app on Vercel](https://vercel.com/docs/frameworks/backend/flask). The checks performed here are local only; this repository has not been deployed to Vercel, and no live Neon/OpenRouter request has been verified.

## 🔧 Configuration

### Environment Variables
- `APP_ENV`: Set to `production` when deploying; SQLite fallback is limited to `development` or `local`
- `DATABASE_URL`: PostgreSQL connection URL; required outside local development
- `DB_SSLMODE`: Optional PostgreSQL SSL mode; defaults to `require`
- `SECRET_KEY`: Flask secret key for sessions
- `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`: server-side translation configuration

### Database Configuration
- Database tables are created explicitly with `.venv/bin/flask --app src.main init-db`
- `create_all()` only creates missing tables; it does not remove existing data
- PostgreSQL connection errors return generic messages and do not include the connection URL
- Local SQLite data is not automatically migrated to Neon

## 📱 Browser Compatibility

- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues or questions:
1. Check the browser console for error messages
2. Verify the Flask server is running
3. Ensure all dependencies are installed
4. Check network connectivity for the deployed version

## 🎯 Future Enhancements

Potential improvements for future versions:
- User authentication and multi-user support
- Note categories and tags
- Rich text formatting (bold, italic, lists)
- File attachments
- Export functionality (PDF, Markdown)
- Dark/light theme toggle
- Offline support with service workers
- Note sharing capabilities

---

**Built with Flask, SQLAlchemy, Neon PostgreSQL, and modern web technologies**

