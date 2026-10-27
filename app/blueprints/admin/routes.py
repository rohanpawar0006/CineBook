import logging
from datetime import datetime, timedelta, timezone
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


# -------------------------------------------------------------------------
# Big-Data Analytics Dashboard & JSON API Endpoints
# -------------------------------------------------------------------------

_ANALYTICS_CACHE = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cached_or_compute(cache_key: str, compute_fn):
    now = datetime.now(timezone.utc).timestamp()
    if cache_key in _ANALYTICS_CACHE:
        val, ts = _ANALYTICS_CACHE[cache_key]
        if now - ts < _CACHE_TTL_SECONDS:
            return val
    result = compute_fn()
    _ANALYTICS_CACHE[cache_key] = (result, now)
    return result


@admin_bp.route("/analytics", methods=["GET"])
@login_required
@admin_required
def analytics_dashboard():
    """Render the dark cinematic admin analytics dashboard."""
    from app.extensions_mongo import mongo
    from app.mongo import analytics_queries

    mongo_db = mongo.get_db()
    is_online = mongo.is_available() and mongo_db is not None
    movies = Movie.query.order_by(Movie.title).all()

    kpis = {}
    total_events = 0
    if is_online:
        kpis = analytics_queries.get_kpis(mongo_db)
        try:
            total_events = mongo_db.booking_events.estimated_document_count()
        except Exception:
            total_events = mongo_db.booking_events.count_documents({})

    return render_template(
        "admin/analytics.html",
        is_online=is_online,
        kpis=kpis,
        total_events=total_events,
        movies=movies,
    )


@admin_bp.route("/analytics/api/<metric>", methods=["GET"])
@login_required
@admin_required
def analytics_api(metric: str):
    """JSON API serving analytical metrics for dashboard charts with 5-minute caching."""
    from flask import jsonify
    from app.extensions_mongo import mongo
    from app.mongo import analytics_queries

    mongo_db = mongo.get_db()
    if not mongo.is_available() or mongo_db is None:
        return jsonify({"error": "MongoDB analytics layer is offline.", "is_online": False}), 503

    # Query filters
    start_str = request.args.get("start_date")
    end_str = request.args.get("end_date")
    movie_id_str = request.args.get("movie_id")
    group_by = request.args.get("group_by", "day")
    limit = int(request.args.get("limit", 10))

    start_date = None
    end_date = None
    if start_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if end_str:
        try:
            end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            pass

    movie_id = int(movie_id_str) if movie_id_str and movie_id_str.isdigit() else None
    cache_key = f"{metric}_{start_str}_{end_str}_{movie_id}_{group_by}_{limit}"

    metric_lower = metric.lower()

    if metric_lower == "kpis":
        data = _get_cached_or_compute(cache_key, lambda: analytics_queries.get_kpis(mongo_db, start_date, end_date))
        return jsonify(data), 200

    elif metric_lower == "revenue":
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_revenue_trends(mongo_db, group_by=group_by, start_date=start_date, end_date=end_date, movie_id=movie_id)
        )
        return jsonify(data), 200

    elif metric_lower == "top-movies":
        sort_by = request.args.get("sort_by", "revenue")
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_top_movies(mongo_db, limit=limit, sort_by=sort_by, start_date=start_date, end_date=end_date)
        )
        return jsonify(data), 200

    elif metric_lower == "heatmap":
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_occupancy_and_peak_heatmap(mongo_db, start_date, end_date)
        )
        return jsonify(data), 200

    elif metric_lower == "payments":
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_payment_method_distribution(mongo_db, start_date, end_date)
        )
        return jsonify(data), 200

    elif metric_lower == "cancellations":
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_cancellation_analytics(mongo_db, start_date, end_date)
        )
        return jsonify(data), 200

    elif metric_lower == "funnel":
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_conversion_funnel(mongo_db, start_date, end_date)
        )
        return jsonify(data), 200

    elif metric_lower == "seats":
        screen_name = request.args.get("screen")
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_seat_popularity(mongo_db, screen_name=screen_name, limit=limit)
        )
        return jsonify(data), 200

    elif metric_lower == "segments":
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_customer_segmentation(mongo_db)
        )
        return jsonify(data), 200

    elif metric_lower == "genres":
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_genre_language_preferences(mongo_db)
        )
        return jsonify(data), 200

    elif metric_lower == "recommendations":
        rec_movie_id = movie_id or 1
        data = _get_cached_or_compute(
            cache_key,
            lambda: analytics_queries.get_movie_recommendations_cooccurrence(mongo_db, target_movie_id=rec_movie_id, limit=limit)
        )
        return jsonify(data), 200

    return jsonify({"error": f"Unknown analytics metric: '{metric}'"}), 404


@admin_bp.route("/analytics/export", methods=["GET"])
@login_required
@admin_required
def export_analytics_csv():
    """Generate and download analytics data as CSV."""
    import csv
    import io
    from flask import Response
    from app.extensions_mongo import mongo
    from app.mongo import analytics_queries

    mongo_db = mongo.get_db()
    if not mongo.is_available() or mongo_db is None:
        flash("Cannot export: MongoDB analytics layer is offline.", "warning")
        return redirect(url_for("admin.analytics_dashboard"))

    export_type = request.args.get("type", "revenue")
    output = io.StringIO()
    writer = csv.writer(output)

    if export_type == "top-movies":
        movies_data = analytics_queries.get_top_movies(mongo_db, limit=50)
        writer.writerow(["Movie ID", "Title", "Genre", "Language", "Total Revenue (INR)", "Tickets Sold", "Bookings Count"])
        for m in movies_data:
            writer.writerow([m.get("movie_id"), m.get("movie_title"), m.get("genre"), m.get("language"), m.get("total_revenue"), m.get("tickets_sold"), m.get("bookings_count")])
        filename = "cinebook_top_movies.csv"

    elif export_type == "payments":
        payments = analytics_queries.get_payment_method_distribution(mongo_db)
        writer.writerow(["Payment Method", "Bookings Count", "Tickets Count", "Total Revenue (INR)"])
        for p in payments:
            writer.writerow([p.get("payment_method"), p.get("bookings_count"), p.get("tickets_count"), p.get("total_revenue")])
        filename = "cinebook_payment_methods.csv"

    elif export_type == "segments":
        seg = analytics_queries.get_customer_segmentation(mongo_db)
        writer.writerow(["Segment", "User Count", "Total Revenue (INR)", "Avg Spend (INR)"])
        for s in seg.get("segments", []):
            writer.writerow([s.get("segment"), s.get("user_count"), s.get("total_revenue"), s.get("avg_spend")])
        filename = "cinebook_customer_segments.csv"

    else:
        # Default: Revenue trends
        trends = analytics_queries.get_revenue_trends(mongo_db, group_by="day")
        writer.writerow(["Period", "Format", "Total Revenue (INR)", "Bookings Count", "Tickets Count"])
        for t in trends:
            writer.writerow([t.get("period"), t.get("format"), t.get("total_revenue"), t.get("bookings_count"), t.get("tickets_count")])
        filename = "cinebook_revenue_trends.csv"

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
