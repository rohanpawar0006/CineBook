from datetime import datetime, timezone
from app.extensions import db


class Booking(db.Model):
    """Booking transaction record."""
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    show_id = db.Column(db.Integer, db.ForeignKey("shows.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="CONFIRMED")  # CONFIRMED or CANCELLED
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", back_populates="bookings")
    show = db.relationship("Show", back_populates="bookings")
    booking_seats = db.relationship("BookingSeat", back_populates="booking", cascade="all, delete-orphan")

    @property
    def is_cancelled(self) -> bool:
        return self.status == "CANCELLED"

    def __repr__(self) -> str:
        return f"<Booking {self.code} ({self.status})>"


class BookingSeat(db.Model):
    """Seat assignment for a specific show and booking.
    The UNIQUE(show_id, seat_id) constraint guarantees zero double bookings at DB level.
    """
    __tablename__ = "booking_seats"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False, index=True)
    show_id = db.Column(db.Integer, db.ForeignKey("shows.id"), nullable=False, index=True)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id"), nullable=False, index=True)

    booking = db.relationship("Booking", back_populates="booking_seats")
    show = db.relationship("Show", back_populates="booking_seats")
    seat = db.relationship("Seat", back_populates="booking_seats")

    __table_args__ = (
        db.UniqueConstraint("show_id", "seat_id", name="uq_show_seat"),
    )

    def __repr__(self) -> str:
        return f"<BookingSeat Show={self.show_id} Seat={self.seat_id} Booking={self.booking_id}>"
