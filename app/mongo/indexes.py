"""MongoDB Index Management for CineBook Big-Data & Analytics.

Idempotently configures compound indexes, unique constraints, and TTL policies
tailored for fast analytical aggregation pipelines and storage efficiency.
"""

import logging
from typing import Optional
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.database import Database
from pymongo.errors import PyMongoError, OperationFailure

logger = logging.getLogger(__name__)

# TTL Duration for raw high-volume event streams (180 days in seconds)
PAGE_VIEW_TTL_SECONDS = 180 * 24 * 60 * 60  # 15,552,000 seconds
SEAT_SELECTION_TTL_SECONDS = 180 * 24 * 60 * 60
SEARCH_EVENTS_TTL_SECONDS = 180 * 24 * 60 * 60


def ensure_timeseries_collection(
    db: Database,
    collection_name: str,
    time_field: str = "timestamp",
    meta_field: Optional[str] = None,
    granularity: str = "seconds",
    expire_after_seconds: Optional[int] = None,
) -> None:
    """Attempt to create a native MongoDB time-series collection if supported."""
    try:
        existing = db.list_collection_names()
        if collection_name not in existing:
            options = {
                "timeseries": {
                    "timeField": time_field,
                    "granularity": granularity,
                }
            }
            if meta_field:
                options["timeseries"]["metaField"] = meta_field
            if expire_after_seconds:
                options["expireAfterSeconds"] = expire_after_seconds
            db.create_collection(collection_name, **options)
            logger.info("Created time-series collection '%s' (timeField=%s)", collection_name, time_field)
    except (OperationFailure, PyMongoError) as exc:
        # Fall back gracefully for mongomock or engines without time-series support
        logger.debug("Could not create native timeseries collection '%s' (%s), using standard collection.", collection_name, exc)


def create_indexes(db: Database) -> None:
    """Idempotently create all analytical and operational indexes on MongoDB collections.

    Index Rationale:
    1. booking_events:
       - booking_id (Unique): Enforces exact 1-to-1 parity with SQL bookings and guarantees
         idempotent sync / upsert operations.
       - (movie_id, created_at): Powers movie-specific revenue reports, time-window sales,
         and top-movie aggregations without full collection scans.
       - show_datetime: Crucial for occupancy by time slot, peak-hour heatmap (weekday x hour),
         and past vs upcoming screening analytics.
       - (user_id, created_at): Powers customer segmentation (frequent vs one-time bookers,
         customer lifetime value, cohort retention, and repeat booking intervals).
       - (status, created_at): Enables instant filtering of CONFIRMED vs CANCELLED bookings
         and calculating cancellation rate trends over time.
       - payment_method: Optimizes payment distribution breakdowns (UPI, GPay, PhonePe, RuPay).
       - (genre, language): Accelerates audience taste profiling and recommendation co-occurrence.
       - created_at: Speeds up global date-range dashboard filters and daily revenue rollups.

    2. page_view_events:
       - timestamp (TTL): Automatically purges raw browsing documents older than 180 days,
         preventing disk exhaustion on multi-million clickstreams.
       - (session_id, timestamp): Enables linear session trajectory reconstruction to compute
         the full conversion funnel (page_view -> seat_selection -> booking).
       - (movie_id, timestamp): Powers movie page view tracking and interest velocity.

    3. seat_selection_events:
       - timestamp (TTL): Purges raw selection events older than 180 days.
       - (session_id, timestamp): Correlates with browsing sessions to calculate cart abandonment.
       - (show_id, action): Identifies hot vs abandoned seat reservation attempts per show.

    4. search_events:
       - timestamp (TTL): Purges old queries after 180 days.
       - (query, timestamp): Powers top search queries and trending keyword metrics.

    5. Summary collections:
       - date / date_str (Unique): Pre-aggregated daily revenue lookups.
       - movie_id (Unique): Pre-aggregated movie scorecard lookups.
    """
    if db is None:
        logger.warning("Cannot create indexes: database instance is None.")
        return

    logger.info("Initializing MongoDB indexes on database: %s", db.name)

    # 1. booking_events indexes
    try:
        booking_indexes = [
            IndexModel([("booking_id", ASCENDING)], unique=True, name="idx_booking_id_unique"),
            IndexModel([("movie_id", ASCENDING), ("created_at", DESCENDING)], name="idx_movie_created"),
            IndexModel([("show_datetime", ASCENDING)], name="idx_show_datetime"),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="idx_user_created"),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)], name="idx_status_created"),
            IndexModel([("payment_method", ASCENDING)], name="idx_payment_method"),
            IndexModel([("genre", ASCENDING), ("language", ASCENDING)], name="idx_genre_language"),
            IndexModel([("created_at", DESCENDING)], name="idx_created_at"),
            IndexModel([("city", ASCENDING), ("created_at", DESCENDING)], name="idx_city_created"),
        ]
        db.booking_events.create_indexes(booking_indexes)
        logger.info("Verified indexes on 'booking_events'.")
    except Exception as exc:
        logger.warning("Warning creating indexes on 'booking_events': %s", exc)

    # 2. page_view_events indexes & TTL
    try:
        page_view_indexes = [
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=PAGE_VIEW_TTL_SECONDS, name="idx_pageview_ttl"),
            IndexModel([("session_id", ASCENDING), ("timestamp", ASCENDING)], name="idx_session_time"),
            IndexModel([("movie_id", ASCENDING), ("timestamp", DESCENDING)], name="idx_pageview_movie_time"),
            IndexModel([("path", ASCENDING)], name="idx_path"),
        ]
        db.page_view_events.create_indexes(page_view_indexes)
        logger.info("Verified indexes on 'page_view_events'.")
    except Exception as exc:
        logger.warning("Warning creating indexes on 'page_view_events': %s", exc)

    # 3. seat_selection_events indexes & TTL
    try:
        seat_selection_indexes = [
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=SEAT_SELECTION_TTL_SECONDS, name="idx_seatselect_ttl"),
            IndexModel([("session_id", ASCENDING), ("timestamp", ASCENDING)], name="idx_seatselect_session"),
            IndexModel([("show_id", ASCENDING), ("action", ASCENDING)], name="idx_seatselect_show_action"),
        ]
        db.seat_selection_events.create_indexes(seat_selection_indexes)
        logger.info("Verified indexes on 'seat_selection_events'.")
    except Exception as exc:
        logger.warning("Warning creating indexes on 'seat_selection_events': %s", exc)

    # 4. search_events indexes & TTL
    try:
        search_indexes = [
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=SEARCH_EVENTS_TTL_SECONDS, name="idx_search_ttl"),
            IndexModel([("query", ASCENDING), ("timestamp", DESCENDING)], name="idx_query_time"),
        ]
        db.search_events.create_indexes(search_indexes)
        logger.info("Verified indexes on 'search_events'.")
    except Exception as exc:
        logger.warning("Warning creating indexes on 'search_events': %s", exc)

    # 5. daily_revenue_summary indexes
    try:
        db.daily_revenue_summary.create_indexes([
            IndexModel([("date_str", ASCENDING)], unique=True, name="idx_daily_rev_date_unique"),
            IndexModel([("date", DESCENDING)], name="idx_daily_rev_date"),
        ])
        logger.info("Verified indexes on 'daily_revenue_summary'.")
    except Exception as exc:
        logger.warning("Warning creating indexes on 'daily_revenue_summary': %s", exc)

    # 6. movie_performance_summary indexes
    try:
        db.movie_performance_summary.create_indexes([
            IndexModel([("movie_id", ASCENDING)], unique=True, name="idx_movie_perf_id_unique"),
            IndexModel([("total_revenue", DESCENDING)], name="idx_movie_perf_revenue"),
            IndexModel([("tickets_sold", DESCENDING)], name="idx_movie_perf_tickets"),
        ])
        logger.info("Verified indexes on 'movie_performance_summary'.")
    except Exception as exc:
        logger.warning("Warning creating indexes on 'movie_performance_summary': %s", exc)
