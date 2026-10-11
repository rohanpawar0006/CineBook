import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import User, Show, Seat, Booking, BookingSeat
from app.services.exceptions import (
    BookingError,
    SeatUnavailableError,
    ShowInPastError,
    InvalidSeatSelectionError,
    CancelWindowClosedError,
    UnauthorizedBookingActionError,
)

logger = logging.getLogger(__name__)


def generate_booking_code() -> str:
    """Generate a unique, friendly booking confirmation code."""
    token = secrets.token_hex(4).upper()
    return f"CB-{token}"


def create_booking(user: User, show_id: int, seat_ids: List[int]) -> Booking:
    """Atomically create a confirmed booking for the specified show and seats.

    Args:
        user: Authenticated user making the booking.
        show_id: ID of the show to book seats for.
        seat_ids: List of seat IDs to reserve (1 to 6 seats).

    Returns:
        Booking: The created and committed Booking instance.

    Raises:
        ShowInPastError: If the show has already started.
        InvalidSeatSelectionError: If seat list is invalid or seats don't belong to the screen.
        SeatUnavailableError: If one or more seats are already booked.
    """
    if not seat_ids or len(seat_ids) == 0:
        raise InvalidSeatSelectionError("At least one seat must be selected.")

    if len(seat_ids) > 6:
        raise InvalidSeatSelectionError("A maximum of 6 seats can be booked in a single transaction.")

    show = Show.query.filter_by(id=show_id).first()
    if not show:
        raise InvalidSeatSelectionError(f"Show with ID {show_id} does not exist.")

    now = datetime.now(timezone.utc)
    show_start = show.start_time
    if show_start.tzinfo is None:
        show_start = show_start.replace(tzinfo=timezone.utc)

    if show_start <= now:
        raise ShowInPastError("Cannot book tickets for a show that has already started.")

    # Validate that all seat IDs belong to the screen of this show
    valid_seats = Seat.query.filter(
        Seat.id.in_(seat_ids),
        Seat.screen_id == show.screen_id
    ).all()

    if len(valid_seats) != len(set(seat_ids)):
        raise InvalidSeatSelectionError("One or more selected seats do not belong to this screen.")

    # Check if any seat is already booked
    already_booked = BookingSeat.query.filter(
        BookingSeat.show_id == show.id,
        BookingSeat.seat_id.in_(seat_ids)
    ).first()

    if already_booked:
        raise SeatUnavailableError("One or more selected seats have already been booked. Please reselect.")

    # Compute total price server-side
    total_amount = len(seat_ids) * show.price

    # Atomic creation within transaction
    try:
        booking = Booking(
            code=generate_booking_code(),
            user_id=user.id,
            show_id=show.id,
            status="CONFIRMED",
            total_amount=total_amount
        )
        db.session.add(booking)
        db.session.flush()

        for seat_id in seat_ids:
            booking_seat = BookingSeat(
                booking_id=booking.id,
                show_id=show.id,
                seat_id=seat_id
            )
            db.session.add(booking_seat)

        db.session.commit()
        logger.info(
            "Booking created successfully: Code=%s, User=%s, Show=%s, Seats=%s, Total=%.2f",
            booking.code, user.email, show.id, seat_ids, float(total_amount)
        )
        return booking

    except IntegrityError as exc:
        db.session.rollback()
        logger.warning(
            "Race condition caught when booking seats %s for show %s: %s",
            seat_ids, show.id, exc
        )
        raise SeatUnavailableError("One or more seats were just booked by another user. Please reselect.")


def cancel_booking(user: User, booking_id: int) -> Booking:
    """Cancel an existing booking and immediately free its seats.

    Args:
        user: User requesting cancellation.
        booking_id: ID of the booking to cancel.

    Returns:
        Booking: The updated Booking instance with CANCELLED status.

    Raises:
        UnauthorizedBookingActionError: If user does not own the booking.
        BookingError: If booking does not exist or is already cancelled.
        CancelWindowClosedError: If cancellation is attempted within 1 hour of showtime.
    """
    booking = Booking.query.filter_by(id=booking_id).first()
    if not booking:
        raise BookingError(f"Booking with ID {booking_id} not found.")

    if booking.user_id != user.id and not user.is_admin:
        raise UnauthorizedBookingActionError("You are not authorized to cancel this booking.")

    if booking.status == "CANCELLED":
        raise BookingError("This booking is already cancelled.")

    now = datetime.now(timezone.utc)
    show_start = booking.show.start_time
    if show_start.tzinfo is None:
        show_start = show_start.replace(tzinfo=timezone.utc)

    # Cutoff rule: Cancellation allowed until 1 hour before show
    if show_start - now < timedelta(hours=1):
        raise CancelWindowClosedError(
            "Cancellations are only permitted up to 1 hour prior to show start time."
        )

    # Atomic cancellation: delete BookingSeat rows to free seats, update status
    BookingSeat.query.filter_by(booking_id=booking.id).delete()
    booking.status = "CANCELLED"
    db.session.commit()

    logger.info("Booking cancelled: Code=%s, User=%s", booking.code, user.email)
    return booking


def get_user_bookings(user_id: int) -> List[Booking]:
    """Retrieve all bookings for a user, ordered with newest first.

    Args:
        user_id: ID of the user.

    Returns:
        List[Booking]: Bookings associated with the user.
    """
    return (
        Booking.query.filter_by(user_id=user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )


def get_booking_by_code(code: str, user: User) -> Optional[Booking]:
    """Retrieve a booking by confirmation code, verifying ownership.

    Args:
        code: Unique booking code.
        user: Requesting user.

    Returns:
        Optional[Booking]: Booking if found and authorized, else None.
    """
    booking = Booking.query.filter_by(code=code).first()
    if not booking:
        return None
    if booking.user_id != user.id and not user.is_admin:
        raise UnauthorizedBookingActionError("Unauthorized access to booking.")
    return booking
