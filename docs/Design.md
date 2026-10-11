# Design.md — UI/UX & Visual Design System

---

## 1. Design Direction

- **Style:** Dark, cinematic, clean. Content (posters, seats) stands out against a calm background.
- **Brand personality:** Modern, trustworthy, a little theatrical.
- **UI philosophy:** Few elements per screen; the primary action is always obvious.
- **Target emotion:** Excitement about the movie, confidence that the booking is safe and correct.

## 2. Color System (CSS variables)

| Token | Hex | Use |
|---|---|---|
| `--color-bg` | `#0F1117` | Page background |
| `--color-surface` | `#181B24` | Cards, panels |
| `--color-surface-2` | `#222633` | Inputs, hover surfaces |
| `--color-border` | `#2E3345` | Borders, dividers |
| `--color-text` | `#F2F4F8` | Primary text |
| `--color-text-muted` | `#A3A9BD` | Secondary text |
| `--color-primary` | `#E50914` | Primary buttons, key actions |
| `--color-primary-hover` | `#C20812` | Primary hover |
| `--color-secondary` | `#3B82F6` | Links, secondary actions |
| `--color-accent` | `#F5B301` | Highlights, ratings, selected seats |
| `--color-success` | `#22C55E` | Confirmations |
| `--color-warning` | `#F59E0B` | Warnings |
| `--color-error` | `#EF4444` | Errors |

**Seat state colors**
- Available: `--color-surface-2` with `--color-border` outline
- Selected: `--color-accent` fill with dark text
- Booked: `#3A3F52` fill, reduced opacity, cursor not-allowed, **with an "X" icon/pattern** (not color alone)

Contrast: body text on bg exceeds 4.5:1. Verify primary button text (white on red) when implementing; adjust if below 4.5:1.

## 3. Typography

- **Font family:** `Inter`, fallback `system-ui, -apple-system, "Segoe UI", sans-serif`. (Load via Google Fonts or self-host; always keep the fallback.)
- **Scale:**

| Role | Size | Weight | Line height |
|---|---|---|---|
| H1 | 2rem | 700 | 1.2 |
| H2 | 1.5rem | 600 | 1.3 |
| H3 | 1.25rem | 600 | 1.3 |
| Body | 1rem | 400 | 1.6 |
| Label | 0.875rem | 500 | 1.4 |
| Button | 0.9375rem | 600 | 1 |
| Caption | 0.75rem | 400 | 1.4 |

## 4. Spacing

4px base scale: `4, 8, 12, 16, 24, 32, 48, 64` (`--space-1` … `--space-8`). Use multiples only. Border radius: 8px (cards, inputs), 6px (seats), 999px (badges).

## 5. Layout

- **Container:** max-width 1100px, centered, 16px side padding (24px on ≥768px).
- **Page structure:** Top navbar → content → simple footer.
- **Movie grid:** CSS Grid, `repeat(auto-fill, minmax(200px, 1fr))`, gap 24px.
- **Breakpoints:** Mobile < 640px · Tablet 640–1023px · Desktop ≥ 1024px.
- **Seat map page:** Screen indicator on top, seat grid centered, sticky summary panel (desktop: right side; mobile: bottom bar).

## 6. Components

- **Buttons:** Primary (red fill), Secondary (outline), Danger (for cancel), Disabled state. Min height 44px.
- **Inputs:** Surface-2 background, 1px border, visible label above, inline error text below in error color.
- **Cards:** Movie card (poster, title, language/genre badges); Booking card (code, movie, show time, seats, status badge).
- **Navigation:** Logo left; links (Movies, My Bookings, Admin if admin); right side login/signup or user name + logout. Collapses to a menu button under 640px.
- **Modals/Confirm dialog:** Used for cancel confirmation. Focus trapped, Esc closes, primary action labeled specifically ("Cancel booking").
- **Tables (admin):** Zebra rows, sticky header, horizontal scroll on mobile.
- **Dropdowns/Selects:** Native `<select>` styled with tokens.
- **Alerts/Flash:** Success, warning, error banners with icon and text; dismissible.
- **Badges:** CONFIRMED (success), CANCELLED (muted/error), language/genre (neutral).
- **Loading state:** Skeleton blocks for the seat map while fetching; button spinner during submit (button disabled to prevent double submit).
- **Empty states:** Friendly message + action, e.g., "No upcoming shows for this movie." / "You have no bookings yet. Browse movies."
- **Error states:** Clear message, what happened, what to do next; custom 403/404/500 pages.

## 7. Interaction Design

- **Hover:** Slight surface lightening; movie cards lift 2px. 
- **Focus:** 2px visible outline in `--color-secondary` with 2px offset on all interactive elements. Never remove outlines without replacement.
- **Active:** Slight darken/press (scale 0.98) on buttons.
- **Seat interaction:** Click/tap or Enter/Space toggles selection; selected count and total update instantly; attempt to select a 7th seat shows an inline message.
- **Form validation:** Validate on submit and on blur; errors appear next to the field, and focus moves to the first error.
- **Feedback:** Success flash on booking/cancel; confirmation page shows booking code prominently with copy button.
- **Transitions:** 150–200ms ease for color/transform only. No decorative animations.

## 8. Accessibility

- Seat grid is keyboard navigable (arrow keys move between seats; Enter/Space selects); each seat has `aria-label` like "Row C seat 5, available" and `aria-pressed` for selection.
- Seat states are distinguished by icon/pattern and label, not color alone.
- All images have alt text; form fields have labels.
- Touch targets ≥ 44×44px (seats at least 32px visually with extra hit area on mobile).
- Respect `prefers-reduced-motion`: disable transitions/transforms.
- Flash messages use `role="status"` / `role="alert"` for errors.

## 9. Responsive Design

| Screen | Behavior |
|---|---|
| Mobile | Single column; navbar collapses; seat grid scrolls horizontally inside its own container if needed; booking summary pinned at bottom |
| Tablet | 2–3 column movie grid; summary below or beside the seat grid |
| Desktop | 4+ column movie grid; seat map with sticky side summary |

Wide content (tables, seat grid) scrolls inside its own container; the page body must never scroll sideways.
