# CineBook 🎬 — Modern Movie Ticket Booking System

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Flask 3.1](https://img.shields.io/badge/flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/pytest-19%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A full-stack, production-ready movie ticket booking web platform tailored for Indian cinema multiplexes. Features real-time visual seat selection, zero double-booking database integrity constraints, digital M-Ticket boarding passes, and a cinema management admin dashboard.

---

## 🌟 Key Features

### 🇮🇳 Tailored for Indian Cinema Lovers
- **INR (₹) Currency**: Multiplex pricing tiers (₹220, ₹280, ₹350, ₹420, ₹450) with zero convenience charges.
- **Indian Blockbuster Catalog**: Seeded with *Kalki 2898 AD*, *Stree 2*, *RRR*, *Jawan*, *Manjummel Boys*, and *Kantara*.
- **Indian Cinema Formats**: Audi 1 (IMAX with Laser) & Audi 2 (Dolby Atmos 4K) with certification tags (`U/A 13+`, `U`, `A`).
- **Payment Simulation**: Seamless checkout with Indian payment methods (UPI, GPay, PhonePe, RuPay, NetBanking).

### 💺 Interactive Live Seat Map
- **Curved Cinema Screen**: Realistic curved multiplex screen with dynamic light projection beam.
- **Dynamic Seat States**:
  - ⚪ **Available**: Subtle slate pill with hover glow.
  - 🟡 **Selected**: Radiant Golden Amber (`#FFB300`) with scale bounce.
  - ⚫ **Sold Out**: Muted dark slate with subtle `✕` (aria-disabled).
- **Anti-Scalping Rule**: Strict 6-seat limit per booking transaction with real-time client & server validation.
- **Accessibility First**: Keyboard operable (`Tab`, `Enter`, `Space`) with dynamic `aria-pressed` states.

### 🔒 Enterprise-Grade Booking Integrity
- **Zero Double-Bookings**: Guaranteed at the database engine level via `UNIQUE(show_id, seat_id)` constraint on `BookingSeat`.
- **Atomic Transactions**: Complete booking succeeds or rolls back cleanly with friendly re-selection feedback.
- **Instant Cancellation & Release**: Cancelling automatically deletes `BookingSeat` rows, immediately returning seats to the auditorium for re-booking (1-hour showtime cutoff rule).

### 🎟 Digital M-Ticket Boarding Pass
- **Cinema Boarding Pass Styling**: Perforated ticket styling with notch cutouts, barcode graphic, and quick copy-to-clipboard booking ID.
- **Print / Save as PDF**: Clean print stylesheets for instant physical ticket or PDF generation.

### 🛡 Admin Management Dashboard
- **Occupancy Tracking**: Live capacity visual progress bars and occupancy percentages per show.
- **Catalog Management**: Add movies, upload poster URLs, or toggle movies active/inactive.
- **Show Scheduling**: Schedule shows across auditoriums with automatic time conflict/overlap prevention.

---

## 🔑 Demo Credentials

| Role | Email | Password | Access Level |
|---|---|---|---|
| **Cinema Admin** | `admin@cinebook.com` | `Admin@123` | Full Admin Dashboard (`/admin`) |
| **Moviegoer** | `user@cinebook.com` | `User@123` | Ticket Booking & History (`/bookings`) |

---

## 🏗 System Architecture

```text
Browser ──► Flask Blueprints ──► Service Layer ──► SQLAlchemy Models ──► SQLite (or PostgreSQL)
              │                     │
              └─ Jinja2 + Vanilla JS └─ Business Rules (Atomic Booking, Freeing Seats)
```

- **Application Factory Pattern**: `create_app()` in `app/__init__.py`.
- **Isolated Service Layer**: Business logic lives purely in `app/services/` (`booking_service.py`, `show_service.py`), keeping route handlers lean.
- **Session Authentication**: Flask-Login + Werkzeug salted password hashing.
- **CSRF Protection**: Flask-WTF tokens enabled on all POST forms.

---

## 🚀 Getting Started (Local Development)

### 1. Clone the Repository
```bash
git clone https://github.com/rohanpawar0006/CineBook.git
cd CineBook
```

### 2. Create & Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```
Ensure `.env` contains:
```env
FLASK_APP=app:create_app
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=dev-secret-key-cinebook-local
DATABASE_URL=sqlite:///cinebook.db
```

### 5. Seed the Database
Populate the database with Indian movies, auditoriums, and showtimes:
```bash
python seed.py
# or using flask CLI
flask seed
```

### 6. Run the Application
```bash
flask --app app run --debug
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 🧪 Running Automated Tests

Run the complete test suite (models, services, routes, and security constraints):
```bash
pytest -v
```
All **19 tests** pass with 100% success rate:
- ✅ Health check endpoint
- ✅ User password hashing & role verification
- ✅ Email uniqueness constraint
- ✅ Screen seat uniqueness constraint
- ✅ `UNIQUE(show_id, seat_id)` double-booking prevention constraint
- ✅ Movie catalog listing & detail 404 handling
- ✅ User signup, login, and logout flows
- ✅ End-to-end seat reservation & cancellation
- ✅ Admin authorization & 403 access control
- ✅ Service-layer atomic booking transaction tests
- ✅ 1-hour cancellation cutoff window enforcement

---

## ☁️ Cloud Deployment (Render / Railway / Heroku)

This repository includes [Procfile](file:///d:/CineBook/Procfile), [wsgi.py](file:///d:/CineBook/wsgi.py), and [render.yaml](file:///d:/CineBook/render.yaml) for zero-config production deployment.

### Deploy on [Render](https://render.com):
1. Sign in to **Render** and click **New +** → **Web Service**.
2. Connect your GitHub repository: `https://github.com/rohanpawar0006/CineBook`.
3. Configure the settings:
   - **Environment:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     gunicorn wsgi:app
     ```
4. Add **Environment Variables**:
   - `SECRET_KEY`: `<your-random-secret-key>`
   - `FLASK_ENV`: `production`
5. Click **Deploy Web Service**.

> **Note on Database**: On startup, `wsgi.py` automatically checks if the database is initialized and auto-seeds the Indian cinema catalog if empty.

---

## 📁 Project Structure

```text
CineBook/
├── app/
│   ├── __init__.py          # Application factory & error handlers (403, 404, 500)
│   ├── config.py            # Environment-driven configurations (Dev, Test, Prod)
│   ├── extensions.py        # SQLAlchemy, LoginManager, CSRFProtect, Migrate
│   ├── models/              # Database models
│   │   ├── user.py          # User account & password hashing
│   │   ├── movie.py         # Movie catalog & metadata
│   │   ├── screen.py        # Screen & Seat models with unique constraints
│   │   ├── show.py          # Show screening schedule & pricing
│   │   └── booking.py       # Booking & BookingSeat double-booking guard
│   ├── services/            # Pure business logic layer
│   │   ├── booking_service.py # Atomic booking & cancellation
│   │   ├── show_service.py  # Catalog queries & seat grid availability
│   │   └── exceptions.py    # Custom domain exceptions
│   ├── blueprints/          # Modular routing blueprints
│   │   ├── auth/            # Signup, login, logout routes & WTForms
│   │   ├── movies/          # Movie catalog & showtime detail routes
│   │   ├── booking/         # Seat map, booking, confirmation, cancel
│   │   └── admin/           # Dashboard, movie CRUD, show scheduling
│   ├── templates/           # Jinja2 presentation templates
│   │   ├── base.html        # Shared layout, navbar, flash messages, footer
│   │   ├── auth/            # Login & signup cards
│   │   ├── movies/          # Catalog grid & movie showtimes
│   │   ├── booking/         # Live seat map, M-Ticket confirmation, my bookings
│   │   ├── admin/           # Admin dashboard, forms, show bookings roster
│   │   └── errors/          # Custom 403, 404, 500 error pages
│   ├── static/              # Frontend static assets
│   │   ├── css/main.css     # Dark cinematic design system & glassmorphism
│   │   └── js/seat-map.js   # Interactive live seat map controller
│   └── utils/
│       └── decorators.py    # @admin_required access control decorator
├── tests/                   # Pytest test suite
│   ├── conftest.py          # App & client fixtures with in-memory DB
│   ├── test_models.py       # Model & constraint tests
│   ├── test_services.py     # Service logic & edge case tests
│   └── test_routes.py       # Route & end-to-end integration tests
├── docs/                    # Complete system specifications & design docs
│   ├── PRD.md               # Product Requirements Document
│   ├── Architecture.md      # System Architecture & schema
│   ├── Design.md            # UI/UX design tokens & visual standards
│   ├── Rules.md             # Development & security guidelines
│   ├── Phases.md            # Roadmap & phase acceptance criteria
│   └── Memory.md            # Project status & historical decisions
├── seed.py                  # Idempotent demo database populator
├── wsgi.py                  # WSGI production server entrypoint
├── app.py                   # Root runner alias
├── Procfile                 # Process file for cloud hosts
├── render.yaml              # Render infrastructure blueprint
├── requirements.txt         # Project dependencies
├── .env.example             # Example environment variables
└── README.md                # Project documentation
```

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
