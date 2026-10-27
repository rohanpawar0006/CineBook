from flask import Blueprint, render_template, abort, request, session
from flask_login import current_user
from app.services import show_service, analytics_service

movies_bp = Blueprint("movies", __name__)


def _detect_device() -> str:
    ua = request.headers.get("User-Agent", "").lower()
    if any(k in ua for k in ["mobile", "android", "iphone"]):
        return "mobile"
    elif any(k in ua for k in ["ipad", "tablet"]):
        return "tablet"
    return "desktop"


@movies_bp.route("/", methods=["GET"])
def index():
    """Homepage displaying the catalog of currently showing movies."""
    search_query = request.args.get("q", "").strip()
    movies = show_service.get_active_movies()
    if search_query:
        movies = [m for m in movies if search_query.lower() in m.title.lower() or search_query.lower() in m.genre.lower()]
        analytics_service.record_search(
            query=search_query,
            results_count=len(movies),
            user_id=current_user.id if current_user.is_authenticated else None,
            session_id=session.get("_id"),
        )

    analytics_service.record_page_view(
        path="/",
        movie_id=None,
        user_id=current_user.id if current_user.is_authenticated else None,
        session_id=session.get("_id"),
        device=_detect_device(),
        referrer=request.referrer,
    )
    return render_template("movies/index.html", movies=movies)


@movies_bp.route("/movies/<int:movie_id>", methods=["GET"])
def detail(movie_id: int):
    """Movie detail page featuring synopsis and upcoming showtimes."""
    movie = show_service.get_movie_by_id(movie_id)
    if not movie:
        abort(404)

    analytics_service.record_page_view(
        path=f"/movies/{movie_id}",
        movie_id=movie.id,
        user_id=current_user.id if current_user.is_authenticated else None,
        session_id=session.get("_id"),
        device=_detect_device(),
        referrer=request.referrer,
    )

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
