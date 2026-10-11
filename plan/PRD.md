# PRD.md — Product Requirements Document

> Legend: **[User]** = provided by user · **[Assumption]** = reasonable assumption · **[Rec]** = recommendation · **[Future]** = possibility, not committed

---

## 1. Product Overview

- **Project name:** CineBook (working name) **[Assumption]**
- **One-line description:** A web app where users browse movies and showtimes, pick seats on a live seat map, and book or cancel tickets.
- **Vision:** A small but correct booking system that demonstrates real-world concerns: seat availability, double-booking prevention, and simple admin management.
- **Problem:** Booking by phone or at the counter is slow and gives no live view of which seats are free.
- **Solution:** Online browsing, visual seat selection, instant confirmation with a booking code.
- **Project type [User]:** Mini project, movie ticket booking system.

## 2. Target Users

| Type | Who | Goals | Pain points |
|---|---|---|---|
| Primary | Moviegoer (customer) | Find a show, pick good seats, get a ticket fast | Not knowing seat availability, slow counter queues |
| Secondary | Theatre admin | Add movies/shows, see bookings | Manual scheduling, no overview |
| Secondary (evaluation) | Faculty / evaluators | See a working demo with sound design | — |

## 3. Goals & Objectives

- **Primary:** Working end-to-end flow: signup → browse → select seats → book → view/cancel booking.
- **Secondary:** Clean, responsive UI; admin panel for content management.
- **Product objective:** Zero double-booked seats under any sequence of requests.
- **Technical objectives:** Clean layered code, relational schema with integrity constraints, automated tests for booking logic, simple local setup.

## 4. Core Features

### MVP

| # | Feature | Description / Why | Interaction & behavior | Inputs → Outputs | Dependencies |
|---|---|---|---|---|---|
| F1 | Signup / Login / Logout | Needed to tie bookings to a person | Forms; session cookie after login | name, email, password → session | DB |
| F2 | Browse movies | Entry point of the user journey | Grid of movie cards with title, language, genre, duration | — → movie list | F-DB seed |
| F3 | Movie detail + showtimes | Choose a show | Shows upcoming shows grouped by date, with price | movie_id → shows | F2 |
| F4 | Seat map & selection | Core feature | Grid of seats: available / selected / booked; click to toggle; max 6 seats per booking **[Assumption]** | show_id → seat states | F3 |
| F5 | Booking confirmation | Finalize purchase | Confirm button → atomic booking; show booking code and summary | show_id, seat_ids → booking | F1, F4 |
| F6 | My bookings | Let users review tickets | List upcoming and past bookings with code, seats, status | user → bookings | F5 |
| F7 | Cancel booking | Free seats if plans change | Cancel allowed until 1 hour before show **[Assumption]**; seats become available again | booking_id → status cancelled | F6 |
| F8 | Admin: manage movies & shows | Content must come from somewhere | Admin-only pages to add/edit/delete movies and create shows | form data → records | F1 (role) |

**Payment [Assumption]:** Payment is **simulated** (no real gateway). Booking is confirmed on button click. No card data is ever collected.

### Post-MVP

- Temporary seat hold (e.g., 5 minutes) while the user checks out
- Admin dashboard: bookings per show, simple revenue totals
- Printable / downloadable ticket (PDF) with QR code
- Search and filter by genre, language, date
- Email confirmation **[Rec: only via a free SMTP/mock]**

### Future possibilities **[Future]**

- Movie recommendations from booking history (ML angle)
- Dynamic pricing based on demand
- Multiple theatres/cities
- Real payment gateway integration

## 5. User Stories

- As a moviegoer, I want to browse current movies, so that I can decide what to watch.
- As a moviegoer, I want to see showtimes and prices, so that I can pick a convenient show.
- As a moviegoer, I want to see which seats are free on a visual map, so that I can choose where to sit.
- As a moviegoer, I want to book multiple seats in one go, so that I can sit with friends or family.
- As a moviegoer, I want a booking code after confirming, so that I can show it at the theatre.
- As a moviegoer, I want to view my bookings, so that I can check details later.
- As a moviegoer, I want to cancel a booking, so that I am not stuck if plans change.
- As an admin, I want to add movies and shows, so that users have something to book.
- As an admin, I want to see bookings for a show, so that I know occupancy.

## 6. Functional Requirements

- FR1: Users register with unique email; passwords are stored hashed.
- FR2: Only logged-in users can book, view bookings, or cancel.
- FR3: The seat map shows each seat as available or booked for the selected show.
- FR4: A booking contains 1–6 seats of the same show.
- FR5: A seat cannot be booked twice for the same show (enforced at DB level, not only in UI).
- FR6: A booking either fully succeeds or fully fails (atomic).
- FR7: Cancelling frees the seats immediately; cancelled bookings stay in history.
- FR8: Past shows cannot be booked.
- FR9: Admin routes are accessible only to users with the admin role.
- FR10: Total price = number of seats × show price **[Assumption: flat price per show]**.

## 7. Non-Functional Requirements

- **Performance:** Pages respond < 500 ms locally; seat map loads in a single query.
- **Scalability:** Single-instance SQLite is enough for the project; design stays portable to PostgreSQL.
- **Reliability:** Booking uses transactions; failures return clear errors, never partial data.
- **Security:** Hashed passwords, CSRF protection, server-side validation, role checks, no secrets in repo.
- **Accessibility:** Keyboard-operable seat selection; seat states not conveyed by color alone.
- **Maintainability:** Layered code, type hints, tests for service layer.
- **Privacy:** Store only name, email, password hash. No payment data.
- **Observability:** Structured logging of auth events and booking outcomes.

## 8. Success Criteria

- A new user can complete signup → booking in under 2 minutes.
- Two simultaneous attempts on the same seat: exactly one succeeds (verified by test).
- All MVP features F1–F8 work in a live demo with seeded data.
- Service-layer test suite passes (target ≥ 80% coverage on `services/`).
- Fresh clone runs with ≤ 5 documented commands.

## 9. Constraints

- **Budget:** ₹0, free tools only.
- **Technology:** Python 3.13, VS Code, local development **[User profile]**.
- **Platform:** Web, desktop and mobile browsers.
- **Time:** Mini-project timeline **TBD** (confirm deadline with faculty).
- **API limits:** No external APIs in MVP.

## 10. Out of Scope

- Real payments, refunds, or wallets
- Multiple cinemas / cities / screens management UI (one theatre, 2–3 seeded screens) **[Assumption]**
- Food ordering, offers, coupons
- Native mobile apps
- Social login (Google, etc.)
- Real-time websockets (page refresh / re-fetch on load is enough)

## 11. Open Questions (TBD)

- Does the college require a specific stack or database? (assumed: free choice)
- Is a report/PPT also required alongside the code? (docs here help but are separate)
- Is a real-looking theatre (e.g., 8×10 grid) fine, or does faculty expect varied seat categories?
