# Memory.md — Project Memory / Development State

> Living document. Update after every meaningful task. Never store secrets here.

---

## Project Status

- **Project:** CineBook (working name), movie ticket booking mini project
- **Current phase:** Phase 0 completed (awaiting Phase 1)
- **Current milestone:** Project scaffold and environment setup
- **Overall completion:** 10% implementation
- **Last completed task:** Phase 0 — Project setup (venv, Flask app factory, /health route, pytest, git)
- **Current task:** None
- **Next task:** Phase 1 — Data models & seed data

## Completed Work

```text
[✓] Documentation system created (6 files)
[✓] Phase 0 — Project setup
[ ] Phase 1 — Data models & seed data
[ ] Phase 2 — Authentication
[ ] Phase 3 — Browse movies & showtimes
[ ] Phase 4 — Seat map & booking
[ ] Phase 5 — My bookings & cancellation
[ ] Phase 6 — Admin panel
[ ] Phase 7 — UI/UX polish
[ ] Phase 8 — Testing & hardening
[ ] Phase 9 — Docs, demo, deployment
```

## Current Architecture

Flask monolith (app factory + blueprints) → service layer → SQLAlchemy → SQLite. Server-rendered Jinja templates with vanilla JS for the seat map. See `Architecture.md`.

## Important Decisions

| Decision | Reason | Alternatives rejected |
|---|---|---|
| Movie ticket booking (not bus/event/flight) | Familiar, visual seat map, right scope for a mini project | Bus (heavier DB), event, flight (too complex) |
| Flask + SQLite + Jinja | Minimal setup, easy to demo and test | FastAPI + React (more moving parts) |
| Simulated payment | No real money/card data; out of scope | Real gateway |
| Double-booking prevented by `UNIQUE(show_id, seat_id)` | Database-level guarantee beats UI checks | App-only checks |
| Cancel deletes `BookingSeat` rows | Frees seats while the unique constraint stays simple | Soft-delete seats with partial index |

## Assumptions (not confirmed by user)

- Single theatre, 2–3 seeded screens, flat price per show
- Max 6 seats per booking; cancel allowed until 1 hour before show
- Project name "CineBook" is a placeholder
- No stack restriction from college (confirm)

## Known Issues

None yet.

## Technical Debt

None yet.

## Environment

- **OS/Editor:** VS Code, Python 3.13
- **Virtual env:** `.venv` in project root
- **Env vars:** `SECRET_KEY`, `DATABASE_URL` (default: SQLite file), `FLASK_ENV` (see `.env.example`; actual values never stored here)
- **Port:** 5000 (Flask default)
- **Commands (planned):**
  - Setup: `python -m venv .venv` then `pip install -r requirements.txt`
  - Run: `flask --app app run --debug`
  - Seed: `python seed.py`
  - Test: `pytest`

## Recent Changes

- Documentation created (PRD, Architecture, Rules, Phases, Design, Memory)

## Next Steps

1. Confirm open questions in `PRD.md` §11 (deadline, report/PPT, stack restrictions)
2. Start Phase 0: scaffold project, app factory, `/health`, git init
3. Move on to Phase 1 only after Phase 0 acceptance criteria are met

## Context for the Next AI Session

Building **CineBook**, a movie ticket booking web app: Flask + SQLAlchemy + SQLite, server-rendered Jinja, vanilla JS seat map. Docs live in `docs/` and are the source of truth (priority: user instruction > PRD > Architecture > Rules > Phases > Design > Memory). No code exists yet; start at **Phase 0** in `Phases.md`. Critical rules: business logic only in `services/`, double-booking guard is `UNIQUE(show_id, seat_id)` in `BookingSeat`, booking runs in one transaction, price computed server-side, payment is simulated, no secrets in repo. Do not skip phases or add dependencies without justification. Update this file after each task.
