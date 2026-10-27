import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, session
from flask_login import login_required, current_user
from app.services import show_service, booking_service, analytics_service
from app.services.exceptions import (
    BookingError,
    SeatUnavailableError,
    ShowInPastError,
    InvalidSeatSelectionError,
    CancelWindowClosedError,
    UnauthorizedBookingActionError,
)

logger = logging.getLogger(__name__)
booking_bp = Blueprint("booking", __name__)


def _detect_device() -> str:
    ua = request.headers.get("User-Agent", "").lower()
    if any(k in ua for k in ["mobile", "android", "iphone"]):
        return "mobile"
    elif any(k in ua for k in ["ipad", "tablet"]):
        return "tablet"
    return "desktop"


@booking_bp.route("/shows/<int:show_id>/seats", methods=["GET"])
@login_required
def seat_map(show_id: int):
    """Render the visual seat map for selecting seats."""
    show = show_service.get_show_by_id(show_id)
    if not show:
        abort(404)

    if show.is_past:
        flash("This show has already started or concluded and cannot be booked.", "warning")
        return redirect(url_for("movies.detail", movie_id=show.movie_id))

    analytics_service.record_page_view(
        path=f"/shows/{show_id}/seats",
        movie_id=show.movie_id,
        user_id=current_user.id if current_user.is_authenticated else None,
        session_id=session.get("_id"),
        device=_detect_device(),
        referrer=request.referrer,
    )

    return render_template("booking/seat_map.html", show=show)


@booking_bp.route("/api/shows/<int:show_id>/seats", methods=["GET"])
@login_required
def api_seats(show_id: int):
    """JSON API endpoint returning seat layout and booked status for a show."""
    grid = show_service.get_show_seat_grid(show_id)
    if not grid:
        return jsonify({"error": "Show not found"}), 404
    return jsonify(grid), 200


@booking_bp.route("/api/shows/<int:show_id>/track-selection", methods=["POST"])
@login_required
def track_seat_selection(show_id: int):
    """Telemetry endpoint tracking seat selection/deselection/abandonment."""
    payload = request.get_json(silent=True) or {}
    action = payload.get("action", "select")
    seat_ids = payload.get("seat_ids", [])
    if action in ["select", "deselect", "abandon"]:
        analytics_service.record_seat_selection(
            session_id=session.get("_id") or str(current_user.id),
            show_id=show_id,
            seat_ids=seat_ids,
            action=action,
            user_id=current_user.id,
        )
    return jsonify({"status": "ok"}), 200


@booking_bp.route("/shows/<int:show_id>/book", methods=["POST"])
@login_required
def book_seats(show_id: int):
    """Process seat reservation form submission atomically."""
    raw_seat_ids = request.form.get("seat_ids", "")
    if not raw_seat_ids:
        flash("Please select at least one seat before confirming.", "warning")
        return redirect(url_for("booking.seat_map", show_id=show_id))

    try:
        seat_ids = [int(sid.strip()) for sid in raw_seat_ids.split(",") if sid.strip()]
    except ValueError:
        flash("Invalid seat selection data.", "danger")
        return redirect(url_for("booking.seat_map", show_id=show_id))

    payment_method = request.form.get("payment_method", "UPI").strip() or "UPI"
    city = request.form.get("city", "Mumbai").strip() or "Mumbai"

    try:
        booking = booking_service.create_booking(
            user=current_user,
            show_id=show_id,
            seat_ids=seat_ids,
            payment_method=payment_method,
            city=city,
        )
        flash(f"Booking confirmed! Your confirmation code is {booking.code}.", "success")
        return redirect(url_for("booking.confirmation", booking_id=booking.id))

    except (SeatUnavailableError, InvalidSeatSelectionError, ShowInPastError) as err:
        logger.warning("Booking failed for user %s: %s", current_user.email, err)
        flash(str(err), "danger")
        return redirect(url_for("booking.seat_map", show_id=show_id))

    except BookingError as err:
        logger.error("Booking error: %s", err)
        flash("An error occurred while creating your booking. Please try again.", "danger")
        return redirect(url_for("booking.seat_map", show_id=show_id))


@booking_bp.route("/bookings/<int:booking_id>/confirmation", methods=["GET"])
@login_required
def confirmation(booking_id: int):
    """Display booking confirmation slip."""
    user_bookings = booking_service.get_user_bookings(current_user.id)
    booking = next((b for b in user_bookings if b.id == booking_id), None)
    if not booking and not current_user.is_admin:
        abort(404)
    return render_template("booking/confirmation.html", booking=booking)


@booking_bp.route("/bookings", methods=["GET"])
@login_required
def my_bookings():
    """Display user's active and past bookings."""
    bookings = booking_service.get_user_bookings(current_user.id)
    return render_template("booking/my_bookings.html", bookings=bookings)


@booking_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel(booking_id: int):
    """Cancel a confirmed booking."""
    try:
        booking_service.cancel_booking(user=current_user, booking_id=booking_id)
        flash("Your booking has been cancelled and your seats released.", "info")
    except CancelWindowClosedError as err:
        flash(str(err), "danger")
    except UnauthorizedBookingActionError:
        abort(403)
    except BookingError as err:
        flash(str(err), "warning")

    return redirect(url_for("booking.my_bookings"))
