import logging
from datetime import timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required
from app.extensions import db
from app.models import Movie, Screen, Show, Booking, BookingSeat
from app.utils.decorators import admin_required
from app.blueprints.admin.forms import MovieForm, ShowForm

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/", methods=["GET"], strict_slashes=False)
@admin_bp.route("", methods=["GET"])
@login_required
@admin_required
def index():
    """Admin dashboard overview with statistics and management tables."""
    movies = Movie.query.order_by(Movie.title).all()
    shows = Show.query.order_by(Show.start_time.desc()).all()
    bookings_count = Booking.query.count()
    screens = Screen.query.all()

    # Pre-calculate occupancy for each show
    show_stats = []
    for s in shows:
        total_seats = len(s.screen.seats)
        booked_seats = BookingSeat.query.filter_by(show_id=s.id).count()
        occupancy_pct = (booked_seats / total_seats * 100) if total_seats > 0 else 0
        show_stats.append({
            "show": s,
            "total_seats": total_seats,
            "booked_seats": booked_seats,
            "occupancy_pct": round(occupancy_pct, 1)
        })

    return render_template(
        "admin/index.html",
        movies=movies,
        show_stats=show_stats,
        total_bookings=bookings_count,
        screens=screens
    )


@admin_bp.route("/movies/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_movie():
    """Add a new movie to the catalog."""
    form = MovieForm()
    if form.validate_on_submit():
        movie = Movie(
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            language=form.language.data.strip(),
            genre=form.genre.data.strip(),
            duration_min=form.duration_min.data,
            poster_url=form.poster_url.data.strip() if form.poster_url.data else None,
            is_active=True
        )
        db.session.add(movie)
        db.session.commit()
        logger.info("Admin created movie: %s", movie.title)
        flash(f"Movie '{movie.title}' added successfully!", "success")
        return redirect(url_for("admin.index"))

    return render_template("admin/movie_form.html", form=form, title="Add New Movie")


@admin_bp.route("/movies/<int:movie_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_movie(movie_id: int):
    """Toggle active/inactive status of a movie."""
    movie = db.session.get(Movie, movie_id)
    if not movie:
        abort(404)

    movie.is_active = not movie.is_active
    db.session.commit()
    status_str = "activated" if movie.is_active else "deactivated"
    flash(f"Movie '{movie.title}' has been {status_str}.", "info")
    return redirect(url_for("admin.index"))


@admin_bp.route("/shows/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_show():
    """Schedule a new show with overlap validation."""
    form = ShowForm()
    # Populate dropdown choices
    form.movie_id.choices = [(m.id, m.title) for m in Movie.query.filter_by(is_active=True).order_by(Movie.title).all()]
    form.screen_id.choices = [(s.id, f"{s.name} ({s.rows}x{s.cols} = {s.rows*s.cols} seats)") for s in Screen.query.order_by(Screen.name).all()]

    if form.validate_on_submit():
        movie = db.session.get(Movie, form.movie_id.data)
        screen = db.session.get(Screen, form.screen_id.data)
        start_time = form.start_time.data
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        duration = timedelta(minutes=movie.duration_min)
        end_time = start_time + duration

        # Check for screening overlaps on the same screen
        existing_shows = Show.query.filter_by(screen_id=screen.id).all()
        has_overlap = False
        for es in existing_shows:
            es_start = es.start_time
            if es_start.tzinfo is None:
                es_start = es_start.replace(tzinfo=timezone.utc)
            es_end = es_start + timedelta(minutes=es.movie.duration_min)

            if not (end_time <= es_start or start_time >= es_end):
                has_overlap = True
                break

        if has_overlap:
            flash(f"Showtime conflicts with an existing screening scheduled in {screen.name}.", "danger")
        else:
            show = Show(
                movie_id=movie.id,
                screen_id=screen.id,
                start_time=start_time,
                price=form.price.data
            )
            db.session.add(show)
            db.session.commit()
            logger.info("Admin created show: Movie=%s, Screen=%s, Time=%s", movie.title, screen.name, start_time)
            flash(f"Show scheduled successfully for {movie.title} in {screen.name}!", "success")
            return redirect(url_for("admin.index"))

    return render_template("admin/show_form.html", form=form, title="Schedule New Show")


@admin_bp.route("/shows/<int:show_id>/bookings", methods=["GET"])
@login_required
@admin_required
def show_bookings(show_id: int):
    """View all bookings and detailed occupancy for a specific show."""
    show = db.session.get(Show, show_id)
    if not show:
        abort(404)

    bookings = Booking.query.filter_by(show_id=show.id).order_by(Booking.created_at.desc()).all()
    total_seats = len(show.screen.seats)
    booked_count = BookingSeat.query.filter_by(show_id=show.id).count()
    occupancy_pct = (booked_count / total_seats * 100) if total_seats > 0 else 0

    return render_template(
        "admin/show_bookings.html",
        show=show,
        bookings=bookings,
        total_seats=total_seats,
        booked_count=booked_count,
        occupancy_pct=round(occupancy_pct, 1)
    )
