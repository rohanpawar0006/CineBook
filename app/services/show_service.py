from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.models import Movie, Show, Screen, Seat, BookingSeat


def get_active_movies() -> List[Movie]:
    """Retrieve all active movies from the catalog.

    Returns:
        List[Movie]: List of currently active movies ordered by title.
    """
    return Movie.query.filter_by(is_active=True).order_by(Movie.title).all()


def get_movie_by_id(movie_id: int) -> Optional[Movie]:
    """Fetch a single movie by its ID.

    Args:
        movie_id: Unique identifier of the movie.

    Returns:
        Optional[Movie]: Movie object if found and active, else None.
    """
    return Movie.query.filter_by(id=movie_id, is_active=True).first()


def get_upcoming_shows_for_movie(movie_id: int) -> List[Show]:
    """Retrieve all future scheduled shows for a movie.

    Args:
        movie_id: ID of the movie.

    Returns:
        List[Show]: Upcoming shows ordered by start time.
    """
    now = datetime.now(timezone.utc)
    return (
        Show.query.filter(Show.movie_id == movie_id, Show.start_time > now)
        .order_by(Show.start_time.asc())
        .all()
    )


def get_show_by_id(show_id: int) -> Optional[Show]:
    """Fetch a single show by its ID.

    Args:
        show_id: Unique identifier of the show.

    Returns:
        Optional[Show]: Show object if found, else None.
    """
    return Show.query.filter_by(id=show_id).first()


def get_show_seat_grid(show_id: int) -> Dict[str, Any]:
    """Retrieve the visual seat grid and current booked status for a show.

    Args:
        show_id: ID of the show.

    Returns:
        Dict[str, Any]: Dictionary containing screen info, seat list with availability,
                        and show pricing.
    """
    show = Show.query.filter_by(id=show_id).first()
    if not show:
        return {}

    screen: Screen = show.screen
    # Query all seats in this screen
    seats: List[Seat] = (
        Seat.query.filter_by(screen_id=screen.id)
        .order_by(Seat.row_label.asc(), Seat.number.asc())
        .all()
    )

    # Query already booked seat IDs for this show
    booked_seat_ids = set(
        row[0]
        for row in BookingSeat.query.filter_by(show_id=show.id).with_entities(BookingSeat.seat_id).all()
    )

    seat_list = []
    for s in seats:
        seat_list.append({
            "id": s.id,
            "row": s.row_label,
            "number": s.number,
            "label": s.label,
            "is_booked": s.id in booked_seat_ids
        })

    return {
        "show_id": show.id,
        "movie_title": show.movie.title,
        "screen_name": screen.name,
        "rows": screen.rows,
        "cols": screen.cols,
        "price": float(show.price),
        "start_time": show.start_time.isoformat(),
        "seats": seat_list
    }
