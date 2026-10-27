# Memory.md — Project Memory / Development State

> Living document. Update after every meaningful task. Never store secrets here.

---

## Project Status

- **Project:** CineBook, movie ticket booking mini project
- **Current phase:** MongoDB Big-Data Layer & Analytics Completed
- **Current milestone:** Hybrid SQL + MongoDB Architecture Verified
- **Overall completion:** 100% Core + Big-Data Analytics Layer
- **Last completed task:** MongoDB event/analytics pipeline, denormalized schemas, compound & TTL indexes, big data generator, 11 aggregation pipelines, dark cinematic analytics dashboard, CSV export, scheduled summary refresh job, and 25 passing automated tests.
- **Current task:** Ready for demonstration and usage
- **Next task:** None

## Completed Work

```text
[✓] Documentation system created (6 files)
[✓] Phase 0 — Project setup
[✓] Phase 1 — Data models & seed data
[✓] Phase 2 — Authentication
[✓] Phase 3 — Browse movies & showtimes
[✓] Phase 4 — Seat map & booking
[✓] Phase 5 — My bookings & cancellation
[✓] Phase 6 — Admin panel
[✓] Phase 7 — UI/UX polish
[✓] Phase 8 — Testing & hardening
[✓] Phase 9 — Docs, demo, deployment
[✓] Big-Data Layer — Hybrid SQL (Transactional) + MongoDB (Analytics)
[✓] Aggregation Suite — 11 Pipelines, $facet, $bucket, $group, Chart.js Dashboard
[✓] Test Suite — 25 passing tests including mongomock and offline degradation
```

## Current Architecture

Hybrid Architecture:
- **Transactional Core (ACID):** Flask Blueprints → Services → SQLAlchemy (SQLite/PostgreSQL) with `UNIQUE(show_id, seat_id)` constraint guaranteeing zero double-bookings.
- **Big-Data & Analytics Layer (OLAP):** Asynchronous fire-and-forget event pipeline → MongoDB (PyMongo) with denormalized events (`booking_events`, `page_view_events`, `seat_selection_events`), compound & TTL indexes, pre-aggregated summaries (`daily_revenue_summary`, `movie_performance_summary` via `$merge`), and dark cinematic admin dashboard (`/admin/analytics`).

## Important Decisions

| Decision | Reason | Alternatives rejected |
|---|---|---|
| Movie ticket booking (not bus/event/flight) | Familiar, visual seat map, right scope for a mini project | Bus (heavier DB), event, flight (too complex) |
| Flask + SQLite + Jinja | Minimal setup, easy to demo and test | FastAPI + React (more moving parts) |
| Simulated payment | No real money/card data; out of scope | Real gateway |
| Double-booking prevented by `UNIQUE(show_id, seat_id)` | Database-level guarantee beats UI checks | App-only checks |
| Cancel deletes `BookingSeat` rows | Frees seats while the unique constraint stays simple | Soft-delete seats with partial index |
| Indian cinema localization | Tailored for Indian audience (₹ INR currency, Indian movies, IMAX Laser/Dolby Atmos formats, M-Ticket) | Generic USD catalog |
| Hybrid SQL + MongoDB Architecture | Keeps SQL as transactional ACID source of truth for seat reservation locks, while offloading millions of clickstream and booking events to MongoDB for zero-join real-time analytics and aggregation | Pure SQL (table locks, slow joins over millions of rows) or Pure NoSQL (lacks rock-solid ACID relational constraints for double-booking guard) |
| Denormalized `booking_events` schema | Embedding movie title, genre, language, screen format, and seat labels directly in the event doc eliminates $lookup / join overhead in aggregations | Normalized document structure requiring multi-collection joins |
| Graceful degradation on MongoDB offline | Application starts and booking transactions succeed even if MongoDB is offline or Atlas cluster is unreachable | Crashing or rolling back bookings when analytics store is unreachable |
| TTL index on `page_view_events` (180 days) | Automatically purges multi-million clickstream documents without manual maintenance | Manual cron cleanup scripts or unbounded database growth |

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
