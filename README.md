# CineBook — Movie Ticket Booking System

A lightweight, reliable movie ticket booking web application built with Flask, SQLAlchemy, SQLite, server-rendered Jinja2 templates, and vanilla JavaScript.

## Tech Stack

- **Backend:** Python 3.13, Flask 3.x
- **Database:** SQLite with Flask-SQLAlchemy ORM
- **Migrations:** Flask-Migrate (Alembic)
- **Authentication:** Flask-Login + Werkzeug secure password hashing
- **Forms & CSRF:** Flask-WTF
- **Testing:** pytest
- **Frontend:** HTML5, Jinja2 templates, custom CSS design system, vanilla JavaScript

## Getting Started

### 1. Clone & Setup Virtual Environment

```bash
# Clone the repository
git clone <repo-url>
cd CineBook

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Ensure `.env` contains:
```env
FLASK_APP=app:create_app
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///cinebook.db
```

### 4. Run the Application

```bash
flask --app app run --debug
```

Visit [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health) to verify the server is running.

### 5. Run Tests

```bash
pytest
```

## Cloud Deployment (Render / Railway / PythonAnywhere)

The repository includes a [Procfile](file:///d:/CineBook/Procfile) and [render.yaml](file:///d:/CineBook/render.yaml) for instant cloud deployment:

### Deploy on Render:
1. Connect your GitHub repository `https://github.com/rohanpawar0006/CineBook`.
2. Select **Web Service**.
3. Set:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt && python seed.py`
   - **Start Command:** `gunicorn "app:create_app()"`
4. Add Environment Variable:
   - `SECRET_KEY`: `<your-random-production-key>`
   - `FLASK_ENV`: `production`

Your CineBook app will be deployed live!

## Project Structure

```text
cinebook/
├── app/
│   ├── __init__.py          # App factory & extension initialization
│   ├── config.py            # Environment-driven configuration
│   ├── extensions.py        # Database, auth, CSRF, migration extensions
│   ├── models/              # SQLAlchemy database models
│   ├── services/            # Isolated business logic layer
│   ├── blueprints/          # Modular route blueprints (auth, movies, booking, admin)
│   ├── templates/           # Jinja2 presentation templates
│   ├── static/              # CSS tokens, JS scripts, assets
│   └── utils/               # Common utilities and decorators
├── tests/                   # Pytest suite
├── docs/                    # Architecture, PRD, Design, Rules, Phases, Memory
├── requirements.txt         # Project dependencies
├── .env.example             # Example environment file
└── README.md                # Project documentation
```

## License

MIT
