from datetime import datetime, timezone
from app.extensions import db


class Show(db.Model):
    """Movie screening schedule model."""
    __tablename__ = "shows"

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False, index=True)
    screen_id = db.Column(db.Integer, db.ForeignKey("screens.id"), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    movie = db.relationship("Movie", back_populates="shows")
    screen = db.relationship("Screen", back_populates="shows")
    bookings = db.relationship("Booking", back_populates="show", cascade="all, delete-orphan")
    booking_seats = db.relationship("BookingSeat", back_populates="show", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("idx_show_movie_time", "movie_id", "start_time"),
    )

    @property
    def is_past(self) -> bool:
        """Check if show has already started or passed."""
        now = datetime.now(timezone.utc)
        start = self.start_time
        if start.tzinfo is None:
            # If stored as naive UTC
            start = start.replace(tzinfo=timezone.utc)
        return start < now

    def __repr__(self) -> str:
        return f"<Show {self.id} Movie={self.movie_id} Time={self.start_time}>"
