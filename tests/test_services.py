from datetime import datetime, timedelta, timezone
import pytest
from app.extensions import db
from app.models import User, Movie, Screen, Seat, Show, Booking, BookingSeat
from app.services import booking_service, show_service
from app.services.exceptions import (
    SeatUnavailableError,
    ShowInPastError,
    InvalidSeatSelectionError,
    CancelWindowClosedError,
    UnauthorizedBookingActionError,
    BookingError,
)


@pytest.fixture
def setup_data(app):
    """Fixture providing user, movie, screen, seats, and upcoming show."""
    user1 = User(name="User 1", email="user1@example.com")
    user1.set_password("pass123")
    user2 = User(name="User 2", email="user2@example.com")
    user2.set_password("pass123")

    screen = Screen(name="Main Screen", rows=2, cols=3)
    movie = Movie(
        title="Dune 2",
        description="Epic sci-fi",
        language="English",
        genre="Sci-Fi",
        duration_min=165
    )
    db.session.add_all([user1, user2, screen, movie])
    db.session.commit()

    # Create 6 seats: A1, A2, A3, B1, B2, B3
    seats = []
    for r in ["A", "B"]:
        for n in [1, 2, 3]:
            s = Seat(screen_id=screen.id, row_label=r, number=n)
            db.session.add(s)
            seats.append(s)
    db.session.commit()

    # Upcoming show 5 hours in future
    show = Show(
        movie_id=movie.id,
        screen_id=screen.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=5),
        price=12.00
    )
    db.session.add(show)
    db.session.commit()

    return {
        "user1": user1,
        "user2": user2,
        "screen": screen,
        "movie": movie,
        "seats": seats,
        "show": show
    }


def test_create_booking_success(setup_data):
    """Test standard valid booking creation."""
    user = setup_data["user1"]
    show = setup_data["show"]
    seats = setup_data["seats"][:2]

    booking = booking_service.create_booking(user, show.id, [s.id for s in seats])
    assert booking.id is not None
    assert booking.status == "CONFIRMED"
    assert booking.code.startswith("CB-")
    assert float(booking.total_amount) == 24.00
    assert len(booking.booking_seats) == 2


def test_create_booking_more_than_six_seats_fails(setup_data):
    """Test max 6 seats constraint."""
    user = setup_data["user1"]
    show = setup_data["show"]

    with pytest.raises(InvalidSeatSelectionError):
        booking_service.create_booking(user, show.id, [1, 2, 3, 4, 5, 6, 7])


def test_create_booking_past_show_fails(setup_data):
    """Test booking rejected on past show."""
    user = setup_data["user1"]
    screen = setup_data["screen"]
    movie = setup_data["movie"]
    seat = setup_data["seats"][0]

    past_show = Show(
        movie_id=movie.id,
        screen_id=screen.id,
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        price=10.00
    )
    db.session.add(past_show)
    db.session.commit()

    with pytest.raises(ShowInPastError):
        booking_service.create_booking(user, past_show.id, [seat.id])


def test_create_booking_already_booked_seat_fails(setup_data):
    """Test booking an already booked seat raises SeatUnavailableError."""
    user1 = setup_data["user1"]
    user2 = setup_data["user2"]
    show = setup_data["show"]
    seat = setup_data["seats"][0]

    booking_service.create_booking(user1, show.id, [seat.id])

    with pytest.raises(SeatUnavailableError):
        booking_service.create_booking(user2, show.id, [seat.id])


def test_cancel_booking_success_and_frees_seats(setup_data):
    """Test cancellation marks booking cancelled and frees seats."""
    user = setup_data["user1"]
    show = setup_data["show"]
    seat = setup_data["seats"][0]

    booking = booking_service.create_booking(user, show.id, [seat.id])
    assert BookingSeat.query.filter_by(show_id=show.id, seat_id=seat.id).count() == 1

    cancelled = booking_service.cancel_booking(user, booking.id)
    assert cancelled.status == "CANCELLED"
    assert BookingSeat.query.filter_by(show_id=show.id, seat_id=seat.id).count() == 0

    # Another user can now book that freed seat
    user2 = setup_data["user2"]
    b2 = booking_service.create_booking(user2, show.id, [seat.id])
    assert b2.status == "CONFIRMED"


def test_cancel_booking_inside_one_hour_fails(setup_data):
    """Test cancellation rejected when show is less than 1 hour away."""
    user = setup_data["user1"]
    screen = setup_data["screen"]
    movie = setup_data["movie"]
    seat = setup_data["seats"][0]

    soon_show = Show(
        movie_id=movie.id,
        screen_id=screen.id,
        start_time=datetime.now(timezone.utc) + timedelta(minutes=30),
        price=10.00
    )
    db.session.add(soon_show)
    db.session.commit()

    booking = booking_service.create_booking(user, soon_show.id, [seat.id])

    with pytest.raises(CancelWindowClosedError):
        booking_service.cancel_booking(user, booking.id)


def test_cancel_booking_unauthorized_user_fails(setup_data):
    """Test another user cannot cancel someone else's booking."""
    user1 = setup_data["user1"]
    user2 = setup_data["user2"]
    show = setup_data["show"]
    seat = setup_data["seats"][0]

    booking = booking_service.create_booking(user1, show.id, [seat.id])

    with pytest.raises(UnauthorizedBookingActionError):
        booking_service.cancel_booking(user2, booking.id)


def test_show_service_seat_grid(setup_data):
    """Test seat grid calculation with booked status."""
    user = setup_data["user1"]
    show = setup_data["show"]
    seat = setup_data["seats"][0]

    grid_before = show_service.get_show_seat_grid(show.id)
    assert len(grid_before["seats"]) == 6
    assert all(s["is_booked"] is False for s in grid_before["seats"])

    booking_service.create_booking(user, show.id, [seat.id])

    grid_after = show_service.get_show_seat_grid(show.id)
    booked_seat_entry = next(s for s in grid_after["seats"] if s["id"] == seat.id)
    assert booked_seat_entry["is_booked"] is True
