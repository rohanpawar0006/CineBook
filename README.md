# CineBook 🎬 — Modern Movie Ticket Booking System

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Flask 3.1](https://img.shields.io/badge/flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/pytest-25%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0%20%7C%20Atlas-green.svg)](https://www.mongodb.com/)
[![Render](https://img.shields.io/badge/Render-Live%20Demo-success?logo=render)](https://cinebook-stza.onrender.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🚀 **Live Demo:** [https://cinebook-stza.onrender.com](https://cinebook-stza.onrender.com)

A full-stack, production-ready movie ticket booking web platform tailored for Indian cinema multiplexes. Features real-time visual seat selection, zero double-booking database integrity constraints, digital M-Ticket boarding passes, cinema management, and a **MongoDB-powered big-data layer** delivering real-time aggregations over millions of booking & browsing events.

---

## 🌟 Key Features

### 🇮🇳 Tailored for Indian Cinema Lovers
- **INR (₹) Currency**: Multiplex pricing tiers (₹220, ₹280, ₹350, ₹420, ₹450) with zero convenience charges.
- **Indian Blockbuster Catalog**: Seeded with *Kalki 2898 AD*, *Stree 2*, *RRR*, *Jawan*, *Manjummel Boys*, and *Kantara*.
- **Indian Cinema Formats**: Audi 1 (IMAX with Laser) & Audi 2 (Dolby Atmos 4K) with certification tags (`U/A 13+`, `U`, `A`).
- **Payment Simulation**: Seamless checkout with Indian payment methods (UPI, GPay, PhonePe, RuPay, NetBanking).

### 📊 Big-Data Analytics & Intelligence Layer
- **Hybrid Storage Architecture**: Relational SQL remains the single transactional source of truth (ACID `UNIQUE(show_id, seat_id)` double-booking guard untouched), while MongoDB stores denormalized event logs (`booking_events`, `page_view_events`, `seat_selection_events`, `search_events`).
- **Graceful Degradation**: Booking and cancellation transactions succeed 100% even if MongoDB is offline or unreachable.
- **High-Throughput Ingestion**: Fire-and-forget ingestion hooks record telemetry without delaying checkout transactions.
- **11 Aggregation Pipelines**: Real-time business intelligence using `$facet`, `$bucket`, `$group`, and `allowDiskUse=True`:
  - Revenue by day/week/month, screen, and audio/visual format
  - Top movies ranked by gross box office and ticket velocity
  - Peak-hour screening heatmap (7 weekdays × 24 hours)
  - Payment method market share (UPI dominant)
  - Cancellation rates overall and per-movie
  - Seat popularity and tier distribution (Classic, Prime, Recliner)
  - E-commerce conversion funnel and cart abandonment telemetry
  - Customer segmentation (One-time, Occasional, Cinephiles) and repeat rate
  - Co-occurrence recommendation engine ("Users who booked X also booked Y")
- **Dark Cinematic Admin Analytics Dashboard**: Accessible at `/admin/analytics` featuring interactive Chart.js visualizations, date & movie filters, and one-click CSV report exports.
- **Scheduled Rollups**: Pre-aggregated collections (`daily_revenue_summary` and `movie_performance_summary`) updated via `$merge` background jobs (`flask refresh-summaries`).

---

## 🔑 Demo Credentials

| Role | Email | Password | Access Level |
|---|---|---|---|
| **Cinema Admin** | `admin@cinebook.com` | `Admin@123` | Full Admin & Big-Data Analytics (`/admin`, `/admin/analytics`) |
| **Moviegoer** | `user@cinebook.com` | `User@123` | Ticket Booking & History (`/bookings`) |

---

## 🏗 System Architecture

```text
Browser ──► Flask Blueprints ──► Services ──► SQLAlchemy Models ──► SQLite / PostgreSQL (Transactional ACID)
               │                     │                                   (Double-booking guard: UNIQUE(show_id, seat_id))
               │                     ▼
               │              Analytics Pipeline (Fire-and-forget ingestion)
               │                     │
               │                     ▼
               │               MongoDB 7 / Atlas (Big-Data OLAP Layer)
               │                     ├── booking_events (Denormalized)
               │                     ├── page_view_events (TTL: 180 days)
               │                     ├── seat_selection_events (Cart telemetry)
               │                     └── search_events
               │                             │
               │                             ▼
               │               Aggregation Pipelines ($facet, $bucket, $group, allowDiskUse)
               │                             ├── Scheduled Summary Job ($merge rollups)
               │                             └── Admin Analytics Dashboard (/admin/analytics, Chart.js)
               │
               └─ Jinja2 + Vanilla JS (Dark Cinematic UI + Live Seat Map)
```

- **Application Factory Pattern**: `create_app()` in `app/__init__.py`.
- **Isolated Service Layer**: Business logic lives in `app/services/` (`booking_service.py`, `show_service.py`, `analytics_service.py`).
- **Connection Pooling**: PyMongo client initialized with connection pooling (`maxPoolSize`, `minPoolSize`) and short server selection timeouts.

---

## 🚀 Getting Started (Local Development)

### 1. Clone the Repository & Activate Environment
```bash
git clone https://github.com/rohanpawar0006/CineBook.git
cd CineBook

# Activate virtual environment
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start MongoDB (Local Docker or Atlas)
Start local MongoDB 7 using Docker Compose:
```bash
docker compose up -d mongo
```
*Note: If running against MongoDB Atlas, set `MONGO_URI` in `.env` to your cluster SRV string.*

### 4. Initialize Database & Seed
```bash
# Seed transactional SQL database (movies, auditoriums, users, shows)
flask seed

# Initialize MongoDB schemas, validators, and compound/TTL indexes
flask init-mongo

# Idempotently sync existing SQL bookings into MongoDB booking_events
flask sync-mongo
```

### 5. Generate Big Data (Indian Cinema Distribution)
Generate realistic large datasets (configurable count, UPI preference, weekend peaks, Pareto distribution):
```bash
# Generate 50,000 bookings and 100,000 page views with seed 42
python scripts/generate_big_data.py --bookings 50000 --page-views 100000 --seed 42

# Or generate the full scale 1,000,000 bookings & 5,000,000 page views:
python scripts/generate_big_data.py --bookings 1000000 --page-views 5000000 --seed 42
```

### 6. Run Aggregation Benchmarks
Benchmark all 11 aggregation pipelines with explain("executionStats") and index comparison:
```bash
python scripts/benchmark_queries.py
```

### 7. Run the Application & Access Dashboard
```bash
flask --app app run --debug
```
- Open Web Application: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**
- Open Big-Data Analytics Dashboard: **[http://127.0.0.1:5000/admin/analytics](http://127.0.0.1:5000/admin/analytics)** (Log in with `admin@cinebook.com` / `Admin@123`).

---

## 🧪 Running Automated Tests

Run the complete test suite (SQL models, services, routes, mongomock aggregations, offline degradation):
```bash
pytest -v
```
All **25 tests** pass with 100% success rate:
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
- ✅ Graceful degradation when MongoDB is offline / unreachable
- ✅ Asynchronous booking & cancellation ingestion in MongoDB
- ✅ Idempotent SQL to MongoDB booking synchronization
- ✅ Deterministic aggregation pipeline test suite (KPIs, Top Movies, Payments, Funnel, Heatmap, Segments)
- ✅ Pre-aggregated summary refresh background job
- ✅ Admin analytics dashboard routes, JSON API, and CSV export
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
