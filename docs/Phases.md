# Phases.md — Implementation Roadmap

Rule: do not start Phase N+1 until Phase N meets its acceptance criteria (unless the user says otherwise). Each phase ends with something testable.

PRD feature mapping: F1 → Phase 2 · F2, F3 → Phase 3 · F4, F5 → Phase 4 · F6, F7 → Phase 5 · F8 → Phase 6.

---

## Phase 0 — Project Setup

### Objective
A running "hello world" Flask app with the agreed structure.

### Features
Project skeleton, virtual environment, config, git.

### Files/Components
`app/__init__.py`, `app/config.py`, `app/extensions.py`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `docs/` (all six docs).

### Dependencies
Python 3.13, VS Code, git.

### Implementation Tasks
- [ ] Create folder structure from `Architecture.md`
- [ ] Create `.venv`, install Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, pytest
- [ ] App factory + one test route (`/health`)
- [ ] `.env.example` with `SECRET_KEY` placeholder
- [ ] Initialize git, first commit

### Testing
`flask run` starts; `/health` returns OK; `pytest` runs (even with one trivial test).

### Acceptance Criteria
Fresh clone + documented steps start the app. No secrets committed.

### Documentation Updates
`Memory.md` (environment, commands, status).

---

## Phase 1 — Data Models & Seed Data

### Objective
Full schema with constraints and demo data.

### Features
All entities from `Architecture.md`; seed script.

### Files/Components
`app/models/*`, `seed.py`, migrations.

### Dependencies
Phase 0.

### Implementation Tasks
- [ ] Models: User, Movie, Screen, Seat, Show, Booking, BookingSeat
- [ ] `UNIQUE(show_id, seat_id)` and `UNIQUE(screen_id, row_label, number)`
- [ ] Seed: 1 admin, 1 user, 5–6 movies, 2 screens (e.g., 8×10), several shows over the next days
- [ ] Initial migration

### Testing
Model tests: unique constraints raise on duplicates; seed runs twice without errors (idempotent or documented reset).

### Acceptance Criteria
DB created from migration; seed produces expected row counts; constraint tests pass.

### Documentation Updates
`Architecture.md` (if schema changed), `Memory.md`.

---

## Phase 2 — Authentication

### Objective
Users can sign up, log in, and log out securely. (F1)

### Features
Signup, login, logout, `admin_required` decorator.

### Files/Components
`blueprints/auth/`, `templates/auth/`, `utils/decorators.py`.

### Dependencies
Phase 1.

### Implementation Tasks
- [ ] Signup form with validation (unique email, password min length)
- [ ] Login/logout with Flask-Login; `next` redirect
- [ ] Password hashing
- [ ] Navbar shows state (login/signup vs. name/logout)
- [ ] `admin_required` decorator

### Testing
Signup success/duplicate email; wrong password; protected route redirects to login; non-admin gets 403 on admin route.

### Acceptance Criteria
All auth tests pass; no plaintext passwords in DB.

### Documentation Updates
`Memory.md`.

---

## Phase 3 — Browse Movies & Showtimes

### Objective
Anyone can view movies and their shows. (F2, F3)

### Features
Movie list, movie detail, show list grouped by date, past shows hidden.

### Files/Components
`blueprints/movies/`, `services/show_service.py`, `templates/movies/`.

### Dependencies
Phase 1 (seed data); base layout.

### Implementation Tasks
- [ ] `/` movie grid
- [ ] `/movies/<id>` with upcoming shows (date, time, screen, price)
- [ ] 404 page for unknown movie
- [ ] Base template + minimal CSS from `Design.md`

### Testing
Only upcoming shows appear; inactive movies hidden; 404 handled.

### Acceptance Criteria
Seeded movies and shows are browsable without login; tests pass.

### Documentation Updates
`Memory.md`.

---

## Phase 4 — Seat Map & Booking (Core)

### Objective
Logged-in users can select seats and complete a booking safely. (F4, F5)

### Features
Seat availability API, seat map UI, atomic booking, confirmation page with booking code.

### Files/Components
`services/booking_service.py`, `blueprints/booking/`, `static/js/seat-map.js`, `templates/booking/`.

### Dependencies
Phases 2 and 3.

### Implementation Tasks
- [ ] `GET /api/shows/<id>/seats` returns seat grid with booked flags
- [ ] Seat map UI: available / selected / booked, max 6 seats, running total
- [ ] `create_booking()` with transaction, validations (past show, seat belongs to screen, max 6, not already booked)
- [ ] Generate unique booking code
- [ ] Confirmation page
- [ ] Friendly handling of "seat just taken"

### Testing
- Successful booking creates correct rows and total
- Booking an already-booked seat fails and creates nothing
- Two sequential attempts on the same seat: exactly one succeeds
- Seat from the wrong screen rejected; more than 6 rejected; past show rejected

### Acceptance Criteria
Double booking impossible in tests; manual run of full flow works in browser.

### Documentation Updates
`Architecture.md` (API details if changed), `Memory.md`.

---

## Phase 5 — My Bookings & Cancellation

### Objective
Users can view and cancel their bookings. (F6, F7)

### Features
Bookings list (upcoming/past), booking detail, cancel with time rule.

### Files/Components
`booking_service.cancel_booking()`, `templates/booking/my_bookings.html`.

### Dependencies
Phase 4.

### Implementation Tasks
- [ ] `/bookings` list with status badges
- [ ] Cancel route with ownership check and 1-hour cutoff
- [ ] Cancel frees seats (delete `BookingSeat` rows, set status)
- [ ] Confirmation prompt before cancel

### Testing
Owner can cancel; other user gets 403/404; cancel inside cutoff rejected; cancelled seats rebookable.

### Acceptance Criteria
Cancel → seat appears available again in the seat map; tests pass.

### Documentation Updates
`Memory.md`.

---

## Phase 6 — Admin Panel

### Objective
Admin can manage movies and shows. (F8)

### Features
Add/edit/deactivate movies; create shows; view bookings per show.

### Files/Components
`blueprints/admin/`, `templates/admin/`.

### Dependencies
Phase 2 (admin role), Phase 3.

### Implementation Tasks
- [ ] Movie CRUD (deactivate instead of delete if bookings exist)
- [ ] Show creation (movie, screen, time, price) with overlap check on the same screen
- [ ] Per-show booking list and occupancy count

### Testing
Non-admin blocked; overlap rejected; new show visible to users.

### Acceptance Criteria
Admin can create a movie and show, and a user can book it, all via the UI.

### Documentation Updates
`PRD.md` (if scope shifts), `Memory.md`.

---

## Phase 7 — UI/UX Polish

### Objective
Make the app look finished and responsive.

### Features
Apply `Design.md` fully, empty/error/loading states, accessibility pass.

### Implementation Tasks
- [ ] Implement design tokens and components
- [ ] Responsive layout check (mobile, tablet, desktop)
- [ ] Keyboard operation of seat map; focus styles
- [ ] Custom 403/404/500 pages
- [ ] Flash message styling

### Testing
Manual checklist at 3 screen widths; keyboard-only booking.

### Acceptance Criteria
Full flow usable on a phone-width screen; no unstyled pages.

### Documentation Updates
`Design.md`, `Memory.md`.

---

## Phase 8 — Testing & Hardening

### Objective
Raise confidence and close security gaps.

### Implementation Tasks
- [ ] Coverage report; target ≥ 80% on `services/`
- [ ] CSRF verified on all POST routes
- [ ] Ownership checks audited
- [ ] Logging reviewed for sensitive data
- [ ] Optional: login rate limiting

### Acceptance Criteria
All tests pass; security checklist in `Rules.md` verified.

### Documentation Updates
`Rules.md` (if rules adjusted), `Memory.md`.

---

## Phase 9 — Documentation, Demo & (Optional) Deployment

### Objective
Ready for submission and demo.

### Implementation Tasks
- [ ] README: setup, run, seed, test, screenshots
- [ ] Demo script (happy path + double-booking demo)
- [ ] Optional free-tier deployment
- [ ] Final doc consistency review

### Acceptance Criteria
A person who has never seen the project can run it from README alone.

---

## Post-MVP Backlog (not scheduled)

Seat hold timer · PDF/QR ticket · search and filters · admin dashboard stats · recommendations (ML) · dynamic pricing
