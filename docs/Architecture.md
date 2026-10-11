# Architecture.md — System Architecture

Derived from `PRD.md`. If they conflict, PRD wins; flag the conflict.

---

## 1. Architecture Overview

A server-rendered monolith. Simple, easy to demo, easy to test.

```
Browser ──► Flask routes (blueprints) ──► Service layer ──► SQLAlchemy models ──► SQLite
              │                              │
              └─ Jinja templates + JS        └─ business rules (booking, cancel, validation)
```

- **Routes** handle HTTP only (parse input, call service, render/redirect).
- **Services** hold business rules (the only place booking/cancel logic lives).
- **Models** define the schema and constraints.
- A small JSON endpoint serves seat availability for the seat map.

## 2. Technology Stack

| Area | Technology | Purpose | Why | Alternatives |
|---|---|---|---|---|
| Language | Python 3.13 | Backend | Already used in the user's environment | — |
| Web framework | Flask | Routing, templates | Minimal, ideal for a mini project | FastAPI (more setup for HTML pages) |
| ORM | Flask-SQLAlchemy | DB access | Constraints, transactions, portability | Raw sqlite3 |
| Database | SQLite | Storage | Zero setup; file-based | PostgreSQL (post-MVP) |
| Auth | Flask-Login + Werkzeug password hashing | Sessions, hashing | Standard, small | Custom sessions |
| Forms/CSRF | Flask-WTF | Validation + CSRF | Security basics built in | Manual |
| Frontend | Jinja2 + HTML/CSS + vanilla JS | UI and seat map | No build step | React (overkill for MVP) |
| Testing | pytest | Unit/integration tests | Standard | unittest |
| Migrations | Flask-Migrate (Alembic) | Schema changes | Safe evolution | Recreate DB (acceptable early) |
| Hosting (optional) | Render / PythonAnywhere free tier | Demo deploy | Free | Local-only demo |

## 3. System Components

| Component | Responsibility |
|---|---|
| `auth` blueprint | Signup, login, logout |
| `movies` blueprint | Movie list, detail, show list |
| `booking` blueprint | Seat map page, create booking, my bookings, cancel |
| `admin` blueprint | CRUD for movies and shows, view bookings (admin role only) |
| `services/booking_service.py` | Validate selection, create booking atomically, cancel |
| `services/show_service.py` | Query shows, compute seat availability |
| `models/` | Entities and constraints |
| `seed.py` | Demo data (movies, screens, seats, shows, admin user) |

## 4. Data Flow

**Booking flow**
1. User opens `/shows/<id>/seats`.
2. Page loads seat grid from `GET /api/shows/<id>/seats`.
3. User selects 1–6 seats and submits `POST /shows/<id>/book` (CSRF token included).
4. Route validates input → calls `booking_service.create_booking(user, show, seat_ids)`.
5. Service opens a transaction, inserts `Booking` and `BookingSeat` rows.
6. If a seat is already taken, the unique constraint raises → transaction rolls back → user sees "Seat(s) just taken, please reselect".
7. On success → redirect to booking confirmation with code.

**Cancel flow:** verify ownership → verify time rule → set status `CANCELLED` → delete that booking's `BookingSeat` rows (frees the seats) → commit.

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
