from app.extensions import db


class Screen(db.Model):
    """Cinema screen / auditorium model."""
    __tablename__ = "screens"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    rows = db.Column(db.Integer, nullable=False)
    cols = db.Column(db.Integer, nullable=False)

    seats = db.relationship("Seat", back_populates="screen", cascade="all, delete-orphan")
    shows = db.relationship("Show", back_populates="screen", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Screen {self.name} ({self.rows}x{self.cols})>"


class Seat(db.Model):
    """Individual seat within a screen."""
    __tablename__ = "seats"

    id = db.Column(db.Integer, primary_key=True)
    screen_id = db.Column(db.Integer, db.ForeignKey("screens.id"), nullable=False, index=True)
    row_label = db.Column(db.String(5), nullable=False)  # e.g. "A", "B"
    number = db.Column(db.Integer, nullable=False)       # e.g. 1, 2, ...

    screen = db.relationship("Screen", back_populates="seats")
    booking_seats = db.relationship("BookingSeat", back_populates="seat", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("screen_id", "row_label", "number", name="uq_screen_seat"),
    )

    @property
    def label(self) -> str:
        """Friendly seat code e.g. 'A1', 'C10'."""
        return f"{self.row_label}{self.number}"

    def __repr__(self) -> str:
        return f"<Seat {self.label} in Screen {self.screen_id}>"
