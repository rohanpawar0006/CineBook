from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import User, Movie, Screen, Seat, Show, Booking, BookingSeat


def test_user_password_hashing(app):
    """Test User password hashing and verification."""
    user = User(name="Alice", email="alice@example.com")
    user.set_password("Secret123")
    assert user.password_hash != "Secret123"
    assert user.check_password("Secret123") is True
    assert user.check_password("WrongPassword") is False
    assert user.is_admin is False


def test_user_admin_flag(app):
    """Test admin role detection."""
    admin = User(name="Admin", email="admin@example.com", role="admin")
    admin.set_password("AdminPass")
    assert admin.is_admin is True


def test_duplicate_user_email_raises(app):
    """Test unique email constraint on User."""
    u1 = User(name="User 1", email="duplicate@example.com")
    u1.set_password("pass1")
    db.session.add(u1)
    db.session.commit()

    u2 = User(name="User 2", email="duplicate@example.com")
    u2.set_password("pass2")
    db.session.add(u2)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_seat_uniqueness_constraint(app):
    """Test UNIQUE(screen_id, row_label, number) constraint on Seat."""
    screen = Screen(name="Test Screen", rows=2, cols=2)
    db.session.add(screen)
    db.session.commit()

    s1 = Seat(screen_id=screen.id, row_label="A", number=1)
    db.session.add(s1)
    db.session.commit()

    s2 = Seat(screen_id=screen.id, row_label="A", number=1)
    db.session.add(s2)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_booking_seat_double_booking_constraint(app):
    """Test UNIQUE(show_id, seat_id) constraint on BookingSeat prevents double booking."""
    user1 = User(name="User 1", email="u1@test.com")
    user1.set_password("pass")
    user2 = User(name="User 2", email="u2@test.com")
    user2.set_password("pass")
    
    screen = Screen(name="Screen IMAX", rows=5, cols=5)
    movie = Movie(
        title="Test Movie",
        description="Description",
        language="English",
        genre="Action",
        duration_min=120
    )
    db.session.add_all([user1, user2, screen, movie])
    db.session.commit()

    seat = Seat(screen_id=screen.id, row_label="A", number=1)
    show = Show(
        movie_id=movie.id,
        screen_id=screen.id,
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        price=15.00
    )
    db.session.add_all([seat, show])
    db.session.commit()

    # User 1 books seat
    booking1 = Booking(
        code="BKG11111",
        user_id=user1.id,
        show_id=show.id,
        status="CONFIRMED",
        total_amount=15.00
    )
    db.session.add(booking1)
    db.session.flush()

    bs1 = BookingSeat(booking_id=booking1.id, show_id=show.id, seat_id=seat.id)
    db.session.add(bs1)
    db.session.commit()

    # User 2 attempts to book the SAME seat for the SAME show
    booking2 = Booking(
        code="BKG22222",
        user_id=user2.id,
        show_id=show.id,
        status="CONFIRMED",
        total_amount=15.00
    )
    db.session.add(booking2)
    db.session.flush()

    bs2 = BookingSeat(booking_id=booking2.id, show_id=show.id, seat_id=seat.id)
    db.session.add(bs2)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
