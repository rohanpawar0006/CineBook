from flask import Blueprint, render_template, abort
from app.services import show_service

movies_bp = Blueprint("movies", __name__)


@movies_bp.route("/", methods=["GET"])
def index():
    """Homepage displaying the catalog of currently showing movies."""
    movies = show_service.get_active_movies()
    return render_template("movies/index.html", movies=movies)


@movies_bp.route("/movies/<int:movie_id>", methods=["GET"])
def detail(movie_id: int):
    """Movie detail page featuring synopsis and upcoming showtimes."""
    movie = show_service.get_movie_by_id(movie_id)
    if not movie:
        abort(404)

    upcoming_shows = show_service.get_upcoming_shows_for_movie(movie.id)
    
    # Group upcoming shows by date (YYYY-MM-DD)
    shows_by_date = {}
    for show in upcoming_shows:
        date_str = show.start_time.strftime("%A, %b %d, %Y")
        if date_str not in shows_by_date:
            shows_by_date[date_str] = []
        shows_by_date[date_str].append(show)

    return render_template(
        "movies/detail.html",
        movie=movie,
        shows_by_date=shows_by_date,
        total_shows=len(upcoming_shows)
    )
