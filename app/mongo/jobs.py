"""Background & Scheduled Data Processing Jobs for CineBook.

Rebuilds pre-aggregated summary collections (daily_revenue_summary and movie_performance_summary)
using high-performance MongoDB $merge aggregation pipelines.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any
from pymongo.database import Database
from pymongo.errors import PyMongoError, OperationFailure
from app.extensions_mongo import mongo

logger = logging.getLogger(__name__)


def _build_daily_pipeline(use_date_trunc: bool, now_utc: datetime):
    day_expr = (
        {"$dateTrunc": {"date": "$created_at", "unit": "day"}}
        if use_date_trunc
        else {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}
    )
    date_str_expr = (
        {"$dateToString": {"format": "%Y-%m-%d", "date": "$_id"}}
        if use_date_trunc
        else "$_id"
    )

    return [
        {"$match": {"status": "CONFIRMED"}},
        {
            "$group": {
                "_id": {
                    "day": day_expr,
                    "format": "$format",
                    "screen": "$screen",
                    "payment": "$payment_method",
                },
                "revenue": {"$sum": "$amount_inr"},
                "bookings": {"$sum": 1},
                "tickets": {"$sum": {"$size": {"$ifNull": ["$seats", []]}}},
            }
        },
        {
            "$group": {
                "_id": "$_id.day",
                "total_revenue": {"$sum": "$revenue"},
                "total_bookings": {"$sum": "$bookings"},
                "total_tickets": {"$sum": "$tickets"},
                "by_format": {
                    "$push": {
                        "format": "$_id.format",
                        "revenue": "$revenue",
                        "tickets": "$tickets",
                    }
                },
                "by_screen": {
                    "$push": {
                        "screen": "$_id.screen",
                        "revenue": "$revenue",
                        "tickets": "$tickets",
                    }
                },
                "by_payment": {
                    "$push": {
                        "payment_method": "$_id.payment",
                        "revenue": "$revenue",
                        "bookings": "$bookings",
                    }
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "date": "$_id",
                "date_str": date_str_expr,
                "total_revenue": "$total_revenue",
                "total_bookings": "$total_bookings",
                "total_tickets": "$total_tickets",
                "by_format": "$by_format",
                "by_screen": "$by_screen",
                "by_payment": "$by_payment",
                "updated_at": {"$literal": now_utc},
            }
        },
    ]


def refresh_daily_revenue_summary(db: Database) -> int:
    """Rebuild daily_revenue_summary pre-aggregated collection with $merge."""
    if db is None:
        logger.warning("MongoDB is offline; cannot refresh daily revenue summary.")
        return 0

    now_utc = datetime.now(timezone.utc)

    try:
        pipeline = _build_daily_pipeline(use_date_trunc=True, now_utc=now_utc)
        merge_stage = {
            "$merge": {
                "into": "daily_revenue_summary",
                "on": "date_str",
                "whenMatched": "replace",
                "whenNotMatched": "insert",
            }
        }
        db.booking_events.aggregate(pipeline + [merge_stage], allowDiskUse=True)
        count = db.daily_revenue_summary.count_documents({})
        logger.info("Refreshed daily_revenue_summary via $merge (%d records).", count)
        return count
    except (OperationFailure, PyMongoError, NotImplementedError) as exc:
        logger.debug("Native $merge/$dateTrunc not supported (%s), falling back to cursor upserts.", exc)
        fallback_pipeline = _build_daily_pipeline(use_date_trunc=False, now_utc=now_utc)
        records = list(db.booking_events.aggregate(fallback_pipeline, allowDiskUse=True))
        for r in records:
            db.daily_revenue_summary.update_one(
                {"date_str": r["date_str"]},
                {"$set": r},
                upsert=True,
            )
        return len(records)


def refresh_movie_performance_summary(db: Database) -> int:
    """Rebuild movie_performance_summary pre-aggregated collection with $merge."""
    if db is None:
        logger.warning("MongoDB is offline; cannot refresh movie performance summary.")
        return 0

    now_utc = datetime.now(timezone.utc)

    pipeline = [
        {
            "$group": {
                "_id": {
                    "movie_id": "$movie_id",
                    "movie_title": "$movie_title",
                    "genre": "$genre",
                    "language": "$language",
                },
                "total_bookings": {"$sum": 1},
                "confirmed_bookings": {
                    "$sum": {"$cond": [{"$eq": ["$status", "CONFIRMED"]}, 1, 0]}
                },
                "cancelled_bookings": {
                    "$sum": {"$cond": [{"$eq": ["$status", "CANCELLED"]}, 1, 0]}
                },
                "total_revenue": {
                    "$sum": {"$cond": [{"$eq": ["$status", "CONFIRMED"]}, "$amount_inr", 0]}
                },
                "tickets_sold": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$status", "CONFIRMED"]},
                            {"$size": {"$ifNull": ["$seats", []]}},
                            0,
                        ]
                    }
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "movie_id": "$_id.movie_id",
                "movie_title": "$_id.movie_title",
                "genre": "$_id.genre",
                "language": "$_id.language",
                "total_revenue": "$total_revenue",
                "tickets_sold": "$tickets_sold",
                "cancellations_count": "$cancelled_bookings",
                "cancellation_rate": {
                    "$cond": [
                        {"$gt": ["$total_bookings", 0]},
                        {"$multiply": [{"$divide": ["$cancelled_bookings", "$total_bookings"]}, 100]},
                        0.0,
                    ]
                },
                "updated_at": {"$literal": now_utc},
            }
        },
    ]

    try:
        merge_stage = {
            "$merge": {
                "into": "movie_performance_summary",
                "on": "movie_id",
                "whenMatched": "replace",
                "whenNotMatched": "insert",
            }
        }
        db.booking_events.aggregate(pipeline + [merge_stage], allowDiskUse=True)
        count = db.movie_performance_summary.count_documents({})
        logger.info("Refreshed movie_performance_summary via $merge (%d records).", count)
        return count
    except (OperationFailure, PyMongoError, NotImplementedError) as exc:
        logger.debug("Native $merge not supported (%s), falling back to cursor upserts.", exc)
        records = list(db.booking_events.aggregate(pipeline, allowDiskUse=True))
        for r in records:
            db.movie_performance_summary.update_one(
                {"movie_id": r["movie_id"]},
                {"$set": r},
                upsert=True,
            )
        return len(records)


def run_summary_refresh_job() -> Dict[str, int]:
    """Execute all summary refresh jobs. Suitable for cron / Render Cron Job invocations."""
    db = mongo.get_db()
    if db is None:
        logger.warning("MongoDB unavailable for summary refresh job.")
        return {"daily_revenue": 0, "movie_performance": 0}

    logger.info("Starting summary collections refresh job...")
    daily_count = refresh_daily_revenue_summary(db)
    movie_count = refresh_movie_performance_summary(db)
    logger.info("Summary collections refreshed: %d daily records, %d movie records.", daily_count, movie_count)
    return {"daily_revenue": daily_count, "movie_performance": movie_count}
