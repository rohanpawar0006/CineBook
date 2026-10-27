# Architecture.md — System Architecture

Derived from `PRD.md`. If they conflict, PRD wins; flag the conflict.

---

## 1. Architecture Overview

A hybrid architecture separating **OLTP (Online Transaction Processing)** from **OLAP (Online Analytical Processing)**:

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

- **Transactional Core (ACID):** SQLAlchemy handles users, shows, seats, and bookings. The `UNIQUE(show_id, seat_id)` constraint prevents double-booking at the database engine level.
- **Big-Data Analytics Layer (OLAP):** PyMongo ingests denormalized booking events, browsing clickstreams, seat selections, and search telemetry asynchronously after SQL transactions commit. If MongoDB is down, transactional bookings proceed uninterrupted (graceful degradation).
- **Analytical Intelligence:** 11 documented aggregation pipelines deliver KPIs, revenue trends, top movies, peak-hour heatmaps, payment share, conversion funnels, customer segmentation, and co-occurrence recommendations.

## 2. Technology Stack

| Area | Technology | Purpose | Why | Alternatives |
|---|---|---|---|---|
| Language | Python 3.13 | Backend | Standard environment | — |
| Web framework | Flask 3.1 | Routing, templates | Minimalist, blueprint architecture | FastAPI, Django |
| Transactional ORM | Flask-SQLAlchemy | ACID transactions | Enforces UNIQUE(show_id, seat_id) constraint | Raw SQL |
| Transactional DB | SQLite / PostgreSQL | Core transactional source of truth | Zero-setup local, PostgreSQL in prod | MySQL |
| Big-Data Layer | MongoDB 7.0 / Atlas | High-volume events & analytics | High write throughput, flexible schema, rich aggregation pipelines | Elasticsearch, ClickHouse |
| MongoDB Driver | PyMongo | Native connection pooling | Official driver, robust pooling & timeouts | MongoEngine, Motor |
| Analytics Mocking | mongomock | Unit & integration tests | Offline testing without live Mongo daemon | Local container only |
| Data Processing | pandas | Benchmark & Jupyter analytics | Fast tabular analytics and exports | Polars |
| Big-Data Generator | Faker (en_IN) | Generates millions of realistic events | Authentic Indian cinema distributions | Custom random scripts |
| Auth | Flask-Login + Werkzeug | Sessions & password hashing | Battle-tested session management | JWT |
| Forms/CSRF | Flask-WTF | Form validation & CSRF tokens | Built-in CSRF protection | Manual tokens |
| Visual Dashboard | Chart.js (CDN) | Interactive analytics visualizations | Lightweight, responsive, zero-build | D3.js, Recharts |
| Testing | pytest | 25 automated unit & integration tests | Standard, fixture-driven | unittest |

## 3. System Components

| Component | Responsibility |
|---|---|
| `auth` blueprint | Signup, login, logout |
| `movies` blueprint | Movie list, detail, show list, browsing telemetry |
| `booking` blueprint | Seat map page, create booking, my bookings, cancel, seat selection telemetry |
| `admin` blueprint | CRUD for movies/shows, view show rosters, dark analytics dashboard (`/admin/analytics`), JSON API, CSV export |
| `services/booking_service.py` | Validate selection, create booking atomically, cancel, triggers analytics events post-commit |
| `services/show_service.py` | Query shows, compute seat availability grid |
| `services/analytics_service.py` | Fire-and-forget ingestion of booking events, page views, seat telemetry, and idempotent SQL backfill |
| `extensions_mongo.py` | Lazily-initialized MongoClient with connection pooling and graceful degradation |
| `mongo/schemas.py` | JSON Schema validators for booking events, page views, seat telemetry, and summaries |
| `mongo/indexes.py` | Idempotent compound and TTL index manager |
| `mongo/analytics_queries.py` | 11 documented aggregation pipelines ($facet, $bucket, $group, allowDiskUse) |
| `mongo/jobs.py` | Scheduled aggregation rollups using $merge for pre-aggregated summary collections |
| `models/` | SQLAlchemy relational entities and constraints |
| `scripts/generate_big_data.py` | High-throughput generator for millions of realistic Indian cinema booking & browsing docs |
| `scripts/benchmark_queries.py` | Query benchmark suite with explain("executionStats") and index comparison |

## 4. Data Flow

**Booking flow**
1. User opens `/shows/<id>/seats` (logs `page_view_events` in MongoDB).
2. User selects seats (logs `seat_selection_events` in MongoDB).
3. User submits `POST /shows/<id>/book` (CSRF token, seat IDs, payment method, city).
4. Route validates input → calls `booking_service.create_booking(user, show, seat_ids, payment_method, city)`.
5. Service opens a transaction, inserts `Booking` and `BookingSeat` rows.
6. If a seat is already taken, `UNIQUE(show_id, seat_id)` raises `IntegrityError` → transaction rolls back → user sees "Seat(s) just taken, please reselect".
7. On commit success:
   - Triggers `analytics_service.record_booking_event(booking, payment_method, city)` (asynchronous fire-and-forget into MongoDB `booking_events`).
   - If MongoDB is down, a warning is logged; booking is never delayed or rolled back.
8. User is redirected to confirmation slip with booking code.

**Cancel flow:**
1. Verify ownership and 1-hour cutoff window.
2. Update booking status to `CANCELLED` and delete `BookingSeat` rows in SQL transaction.
3. On commit success, triggers `analytics_service.record_cancellation_event(booking)` in MongoDB (`status: "CANCELLED"`, sets `cancelled_at`).

## 5. API Architecture

- **Style:** Server-rendered pages (form POSTs) plus one small JSON endpoint.
- **Auth:** Session cookie (Flask-Login).
- **Errors:** Flash messages for page flows; JSON `{ "error": "..." }` with proper status for the API.
- **Validation:** Server-side always; client-side is convenience only.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/` | – | Movie list |
| GET | `/movies/<id>` | – | Movie detail + shows |
| GET/POST | `/signup`, `/login` | – | Auth forms |
| POST | `/logout` | user | Logout |
| GET | `/shows/<id>/seats` | user | Seat map page |
| GET | `/api/shows/<id>/seats` | user | JSON: seats and booked status |
| POST | `/shows/<id>/book` | user | Create booking |
| GET | `/bookings` | user | My bookings |
| POST | `/bookings/<id>/cancel` | owner | Cancel |
| GET/POST | `/admin/movies`, `/admin/shows` | admin | Manage content |

No other endpoints without updating this table.

## 6. Database Architecture

**Entities**

- **User**: id, name, email (unique), password_hash, role (`user`/`admin`), created_at
- **Movie**: id, title, description, language, genre, duration_min, poster_url (nullable), is_active
- **Screen**: id, name, rows, cols
- **Seat**: id, screen_id (FK), row_label, number — unique (screen_id, row_label, number)
- **Show**: id, movie_id (FK), screen_id (FK), start_time, price
- **Booking**: id, code (unique), user_id (FK), show_id (FK), status (`CONFIRMED`/`CANCELLED`), total_amount, created_at
- **BookingSeat**: id, booking_id (FK), show_id (FK), seat_id (FK) — **unique (show_id, seat_id)**

**Relationships:** Movie 1–N Show; Screen 1–N Seat; Screen 1–N Show; User 1–N Booking; Booking 1–N BookingSeat; Show 1–N Booking.

**Key integrity rule:** `UNIQUE(show_id, seat_id)` on `BookingSeat` is the double-booking guard. Cancelled bookings delete their `BookingSeat` rows so the seat becomes free again.

**Indexes:** Show(movie_id, start_time), Booking(user_id), BookingSeat(show_id).

**Data lifecycle:** Bookings are kept as history. Shows in the past remain for records.

## 7. Folder Structure

```text
cinebook/
├── app/
│   ├── __init__.py          # app factory, extensions
│   ├── config.py            # config classes (env-driven)
│   ├── extensions.py        # db, login_manager, csrf, migrate
│   ├── models/              # SQLAlchemy models (one file per entity group)
│   ├── services/            # business logic (booking, shows)
│   ├── blueprints/
│   │   ├── auth/
│   │   ├── movies/
│   │   ├── booking/
│   │   └── admin/
│   ├── templates/           # Jinja2 (base.html + per-blueprint folders)
│   ├── static/
│   │   ├── css/
│   │   ├── js/              # seat-map.js etc.
│   │   └── img/
│   └── utils/               # helpers (booking code, decorators like admin_required)
├── tests/                   # pytest (services first, routes second)
├── docs/                    # PRD, Architecture, Rules, Phases, Design, Memory
├── seed.py                  # demo data
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 8. Security Architecture

- **Auth:** Hashed passwords (Werkzeug), session cookies with `HttpOnly`, `SameSite=Lax`.
- **Authorization:** `login_required` on user routes; `admin_required` decorator on admin routes; ownership check on cancel and view.
- **Secrets:** `SECRET_KEY` from environment; `.env` is git-ignored; `.env.example` has placeholders only.
- **Input validation:** WTForms validators; ID parameters validated; seat IDs must belong to the show's screen.
- **CSRF:** Flask-WTF on all POST forms.
- **Injection:** ORM only, no string-built SQL; Jinja auto-escaping stays on.
- **Rate limiting:** Post-MVP (Flask-Limiter on login) **[Rec]**.
- **Sensitive data:** No payment data collected; never log passwords.

## 9. Scalability

Out of scope for MVP. If needed: move to PostgreSQL, add row-level locking or seat holds with Redis, run behind gunicorn with multiple workers, cache movie lists.

## 10. Failure Points

| Failure | Handling |
|---|---|
| Two users pick the same seat | DB unique constraint → rollback → friendly message → reload seat map |
| User tampers with seat IDs | Server validates seats belong to the show's screen |
| Booking for past show | Service rejects with a clear error |
| DB locked (SQLite under writes) | Short transactions; retry once; log |
| Cancel after cutoff | Service rejects; UI hides the button |
| Session expiry mid-booking | Redirect to login, preserve `next` URL |
