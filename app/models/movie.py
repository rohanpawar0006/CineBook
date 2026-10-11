from datetime import datetime, timezone
from app.extensions import db


class Movie(db.Model):
    """Movie catalog model."""
    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    duration_min = db.Column(db.Integer, nullable=False)
    poster_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    shows = db.relationship("Show", back_populates="movie", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Movie {self.title}>"
