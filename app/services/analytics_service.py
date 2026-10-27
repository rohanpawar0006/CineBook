"""Analytics & Big-Data Ingestion Service.

Captures fire-and-forget telemetry (bookings, cancellations, page views, seat selections,
and search queries) into MongoDB without ever blocking or rolling back SQL transactions.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pymongo import UpdateOne
from pymongo.errors import PyMongoError
from app.extensions_mongo import mongo

logger = logging.getLogger(__name__)


def _infer_screen_format(screen_name: str) -> str:
    """Infer visual/audio projection format from screen title."""
    lower = screen_name.lower()
    if "imax" in lower:
        return "IMAX with Laser"
    elif "dolby" in lower or "atmos" in lower:
        return "Dolby Atmos 4K"
    elif "4dx" in lower:
        return "4DX"
    elif "ice" in lower:
        return "ICE"
    return "Standard 2D"


def _infer_seat_category(row_label: str) -> str:
    """Classify seat row into Indian multiplex tiers (Recliner, Prime, Classic)."""
    row = row_label.upper()
    if row in ["G", "H", "I", "J"]:
        return "Recliner"
    elif row in ["C", "D", "E", "F"]:
        return "Prime"
    return "Classic"


def record_booking_event(
    booking,
    payment_method: str = "UPI",
    city: str = "Mumbai",
) -> None:
    """Fire-and-forget ingestion of a confirmed booking into MongoDB.
    
    Must be called AFTER the SQL transaction commits.
    Catches all exceptions to ensure transactional safety.
    """
    try:
        db = mongo.get_db()
        if db is None:
            return

        show = booking.show
        movie = show.movie
        screen = show.screen

        # Collect seat labels and categories
        seats: List[str] = []
        categories: List[str] = []
        for bs in booking.booking_seats:
            if bs.seat:
                seats.append(bs.seat.label)
                categories.append(_infer_seat_category(bs.seat.row_label))

        show_dt = show.start_time
        if show_dt.tzinfo is None:
            show_dt = show_dt.replace(tzinfo=timezone.utc)

        created_dt = booking.created_at
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)

        doc: Dict[str, Any] = {
            "booking_id": int(booking.id),
            "user_id": int(booking.user_id),
            "movie_id": int(movie.id),
            "movie_title": str(movie.title),
            "genre": str(movie.genre),
            "language": str(movie.language),
            "show_id": int(show.id),
            "screen": str(screen.name),
            "format": _infer_screen_format(screen.name),
            "show_datetime": show_dt,
            "seats": seats,
            "seat_categories": categories,
            "amount_inr": float(booking.total_amount),
            "payment_method": payment_method,
            "status": "CONFIRMED",
            "city": city,
            "created_at": created_dt,
            "cancelled_at": None,
        }

        db.booking_events.update_one(
            {"booking_id": doc["booking_id"]},
            {"$set": doc},
            upsert=True
        )
        logger.debug("Ingested booking_event in Mongo for booking_id=%s", booking.id)
    except Exception as exc:
        logger.warning("Graceful degradation: Failed to record booking_event in MongoDB: %s", exc)


def record_cancellation_event(booking) -> None:
    """Fire-and-forget update when a booking is cancelled.
    
    Must be called AFTER the SQL transaction commits.
    """
    try:
        db = mongo.get_db()
        if db is None:
            return

        now_utc = datetime.now(timezone.utc)
        res = db.booking_events.update_one(
            {"booking_id": int(booking.id)},
            {
                "$set": {
                    "status": "CANCELLED",
                    "cancelled_at": now_utc,
                }
            }
        )
        if res.matched_count == 0:
            # Document wasn't present; upsert it with CANCELLED state
            record_booking_event(booking)
            db.booking_events.update_one(
                {"booking_id": int(booking.id)},
                {"$set": {"status": "CANCELLED", "cancelled_at": now_utc}}
            )
        logger.debug("Ingested cancellation_event in Mongo for booking_id=%s", booking.id)
    except Exception as exc:
        logger.warning("Graceful degradation: Failed to record cancellation_event in MongoDB: %s", exc)


def record_page_view(
    path: str,
    movie_id: Optional[int] = None,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    device: str = "desktop",
    referrer: Optional[str] = None,
) -> None:
    """Ingest a browsing page-view event."""
    try:
        db = mongo.get_db()
        if db is None:
            return

        doc = {
            "session_id": session_id or "anon_session",
            "user_id": int(user_id) if user_id else None,
            "path": path,
            "movie_id": int(movie_id) if movie_id else None,
            "device": device if device in ["mobile", "desktop", "tablet"] else "desktop",
            "referrer": referrer,
            "timestamp": datetime.now(timezone.utc),
        }
        db.page_view_events.insert_one(doc)
    except Exception as exc:
        logger.warning("Failed to record page_view event in MongoDB: %s", exc)


def record_seat_selection(
    session_id: str,
    show_id: int,
    seat_ids: List[int],
    action: str,
    user_id: Optional[int] = None,
) -> None:
    """Ingest seat interaction / cart telemetry (select, deselect, abandon)."""
    try:
        db = mongo.get_db()
        if db is None:
            return

        doc = {
            "session_id": session_id,
            "user_id": int(user_id) if user_id else None,
            "show_id": int(show_id),
            "seat_ids": [int(s) for s in seat_ids],
            "action": action,
            "timestamp": datetime.now(timezone.utc),
        }
        db.seat_selection_events.insert_one(doc)
    except Exception as exc:
        logger.warning("Failed to record seat_selection event in MongoDB: %s", exc)


def record_search(
    query: str,
    results_count: int,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> None:
    """Ingest search queries and results count telemetry."""
    try:
        db = mongo.get_db()
        if db is None:
            return

        doc = {
            "query": query.strip(),
            "results_count": int(results_count),
            "user_id": int(user_id) if user_id else None,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc),
        }
        db.search_events.insert_one(doc)
    except Exception as exc:
        logger.warning("Failed to record search event in MongoDB: %s", exc)


def bulk_insert_events(collection_name: str, documents: List[Dict[str, Any]], batch_size: int = 5000) -> int:
    """Perform batched insert_many with ordered=False for high-throughput big data loading."""
    db = mongo.get_db()
    if db is None or not documents:
        return 0

    inserted = 0
    collection = db[collection_name]
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        try:
            res = collection.insert_many(batch, ordered=False)
            inserted += len(res.inserted_ids)
        except PyMongoError as exc:
            logger.warning("Partial failure during bulk insert into %s: %s", collection_name, exc)
    return inserted


def sync_sql_bookings_to_mongo(batch_size: int = 500) -> int:
    """Idempotently backfills all SQL bookings into MongoDB booking_events using bulk upserts."""
    from app.models import Booking

    db = mongo.get_db()
    if db is None:
        logger.warning("MongoDB is offline; cannot sync SQL bookings.")
        return 0

    bookings = Booking.query.order_by(Booking.id.asc()).all()
    if not bookings:
        logger.info("No SQL bookings found to synchronize.")
        return 0

    total_synced = 0
    operations = []

    for booking in bookings:
        show = booking.show
        movie = show.movie
        screen = show.screen

        seats: List[str] = []
        categories: List[str] = []
        for bs in booking.booking_seats:
            if bs.seat:
                seats.append(bs.seat.label)
                categories.append(_infer_seat_category(bs.seat.row_label))

        show_dt = show.start_time
        if show_dt.tzinfo is None:
            show_dt = show_dt.replace(tzinfo=timezone.utc)

        created_dt = booking.created_at
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)

        doc = {
            "booking_id": int(booking.id),
            "user_id": int(booking.user_id),
            "movie_id": int(movie.id),
            "movie_title": str(movie.title),
            "genre": str(movie.genre),
            "language": str(movie.language),
            "show_id": int(show.id),
            "screen": str(screen.name),
            "format": _infer_screen_format(screen.name),
            "show_datetime": show_dt,
            "seats": seats,
            "seat_categories": categories,
            "amount_inr": float(booking.total_amount),
            "payment_method": "UPI",  # default for backfilled bookings
            "status": str(booking.status),
            "city": "Mumbai",
            "created_at": created_dt,
            "cancelled_at": created_dt if booking.status == "CANCELLED" else None,
        }

        operations.append(
            UpdateOne({"booking_id": doc["booking_id"]}, {"$set": doc}, upsert=True)
        )

        if len(operations) >= batch_size:
            try:
                res = db.booking_events.bulk_write(operations, ordered=False)
                total_synced += (res.upserted_count + res.modified_count + res.matched_count)
            except TypeError:
                for op in operations:
                    db.booking_events.update_one(op._filter, op._doc, upsert=True)
                total_synced += len(operations)
            operations = []

    if operations:
        try:
            res = db.booking_events.bulk_write(operations, ordered=False)
            total_synced += (res.upserted_count + res.modified_count + res.matched_count)
        except TypeError:
            for op in operations:
                db.booking_events.update_one(op._filter, op._doc, upsert=True)
            total_synced += len(operations)

    logger.info("Successfully synced %s SQL bookings into MongoDB booking_events.", len(bookings))
    return len(bookings)
