# Rules.md — Development & AI Coding Rules

The AI coding agent MUST follow these rules unless the user explicitly says otherwise.

---

## 1. General Coding Rules

- **Style:** PEP 8; format with `black`, lint with `ruff` (dev tools only).
- **Naming:** `snake_case` for functions/variables/files, `PascalCase` for classes, `UPPER_CASE` for constants. DB tables are plural snake_case.
- **Type hints:** Required on all service-layer functions and public helpers.
- **Docstrings:** One short docstring on every service function describing behavior and raised errors.
- **File organization:** Follow the folder structure in `Architecture.md`. One responsibility per module.
- **Functions:** Small and single-purpose. No function over ~40 lines without good reason.
- **Logging:** Use Python `logging` (never `print`) for auth events, bookings, cancellations, and errors.
- **Testing:** Every service function gets tests. Every bug fix gets a regression test.

## 2. Technology Rules

### MUST USE
- Python 3.13, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, SQLite, pytest
- Werkzeug password hashing
- Application factory pattern and blueprints

### PREFER
- Server-rendered Jinja pages; JS only where interaction needs it (seat map)
- Database constraints over application-only checks
- Plain CSS with CSS variables from `Design.md`

### DO NOT USE
- Front-end frameworks (React/Vue) or CSS frameworks in MVP, unless the user approves
- Raw SQL string concatenation
- Global mutable state for data
- Real payment SDKs or any collection of card data
- `eval`, `exec`, or `pickle` on user input
- `print` debugging left in committed code

**Dependency rule:** Never add a dependency without stating (a) why it is needed, (b) what was considered instead, and (c) updating `requirements.txt` and `Architecture.md`.

## 3. Architecture Rules

- Follow `Architecture.md`. No structural changes without approval and doc updates.
- Routes contain no business logic. Business rules live in `services/`.
- Booking and cancel logic exists **only** in `booking_service.py`. Do not duplicate it in routes, templates, or JS.
- Reuse helpers/components before writing new ones.
- No abstractions "for the future." Build what the current phase needs.

## 4. AI Coding Rules

1. Understand existing code before changing it.
2. Read the relevant docs and `Memory.md` before implementing.
3. Follow the current architecture.
4. Do not rewrite working code unnecessarily.
5. Do not add dependencies without justification.
6. Do not change APIs/contracts/schema without updating docs.
7. Do not silently change requirements. Raise it, then update `PRD.md`.
8. Do not remove existing functionality unless explicitly told.
9. Keep changes within the current phase in `Phases.md`.
10. Test before calling a task complete, and say exactly what was tested.

## 5. Error Handling

- **Detect:** Validate inputs at the route (form validation) and again in the service (business rules).
- **Handle:** Services raise specific exceptions (e.g., `SeatUnavailableError`, `ShowInPastError`, `CancelWindowClosedError`). Routes catch them and show friendly messages.
- **Log:** Log unexpected exceptions with stack traces; log expected business errors at INFO/WARNING without sensitive data.
- **Display:** Plain-language messages, no stack traces or SQL in the UI. Custom 404/403/500 pages.
- **Retry:** Do not auto-retry bookings. Ask the user to reselect. A single retry is allowed only for "database is locked".
- **Escalate:** Unknown errors return a generic 500 page and are logged.
- **Never hide errors silently.** No bare `except:` and no `except Exception: pass`.

## 6. Security Rules

Never:
- Hardcode secrets or commit `.env`, API keys, or credentials
- Trust unvalidated user input (including hidden form fields and IDs in URLs)
- Bypass or disable CSRF, auth, or role checks to make something work
- Store plaintext passwords or log them
- Let a user view or cancel another user's booking

Always:
- Check `current_user` ownership on booking-related routes
- Validate that selected seats belong to the show's screen
- Keep Jinja auto-escaping enabled (no `|safe` on user content)

## 7. Booking Integrity Rules (project-specific)

- Double-booking prevention is enforced by `UNIQUE(show_id, seat_id)` in `BookingSeat`. Never remove or weaken it.
- Booking creation runs in one transaction: all seats succeed or none.
- Cancelling deletes that booking's `BookingSeat` rows and sets status to `CANCELLED` in the same transaction.
- Max 6 seats per booking; past shows are never bookable.
- Price is computed on the server. Never trust a price from the client.

## 8. AI/LLM Rules

No AI/LLM features in MVP. If the post-MVP recommendation feature is added, this section must be expanded first (model choice, data privacy, fallbacks).

**Always:** The AI agent must not claim an action was completed if it was not actually completed. If tests were not run, say so.

## 9. Change Management

Before any major change, state:
- What is changing
- Why
- Files affected
- Risks
- Whether docs need updating

Major = schema change, new dependency, new endpoint, changed booking rules, folder restructure.

## 10. Git & Workflow

- Small commits, imperative messages (`Add seat map endpoint`).
- One branch per phase is recommended: `phase-3-core-booking`.
- Never commit `.env`, the SQLite DB file, `__pycache__`, or `.venv`.
