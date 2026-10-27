"""MongoDB Schemas, Validators, and Collection Definitions.

Defines JSON Schema validators for big-data events and pre-aggregated summary collections.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# 1. Booking Events (Denormalized event log for bookings and cancellations)
BOOKING_EVENTS_SCHEMA: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "booking_id",
            "user_id",
            "movie_id",
            "movie_title",
            "genre",
            "language",
            "show_id",
            "screen",
            "format",
            "show_datetime",
            "seats",
            "amount_inr",
            "payment_method",
            "status",
            "city",
            "created_at",
        ],
        "properties": {
            "booking_id": {"bsonType": "int", "description": "SQL booking ID (unique reference)"},
            "user_id": {"bsonType": "int", "description": "SQL user ID"},
            "movie_id": {"bsonType": "int", "description": "SQL movie ID"},
            "movie_title": {"bsonType": "string", "description": "Denormalized movie title"},
            "genre": {"bsonType": "string", "description": "Movie primary genre"},
            "language": {"bsonType": "string", "description": "Movie primary language/audio track"},
            "show_id": {"bsonType": "int", "description": "SQL showtime ID"},
            "screen": {"bsonType": "string", "description": "Screen auditorium name"},
            "format": {
                "enum": ["IMAX with Laser", "Dolby Atmos 4K", "Standard 2D", "4DX", "ICE"],
                "description": "Projection and sound format",
            },
            "show_datetime": {"bsonType": "date", "description": "Show start timestamp"},
            "seats": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
                "description": "List of seat labels, e.g. ['A1', 'A2']",
            },
            "seat_categories": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
                "description": "Categories of seats, e.g. ['Recliner', 'Prime', 'Classic']",
            },
            "amount_inr": {"bsonType": ["double", "int", "decimal"], "description": "Total price in INR"},
            "payment_method": {
                "enum": ["UPI", "GPay", "PhonePe", "RuPay", "NetBanking", "Credit/Debit Card", "Paytm"],
                "description": "Payment instrument used",
            },
            "status": {
                "enum": ["CONFIRMED", "CANCELLED"],
                "description": "Lifecycle state of the booking",
            },
            "city": {"bsonType": "string", "description": "Metro/City of booking"},
            "created_at": {"bsonType": "date", "description": "Timestamp when booking was created"},
            "cancelled_at": {"bsonType": ["date", "null"], "description": "Timestamp when booking was cancelled, if any"},
        },
    }
}

# 2. Page View Events (High-volume browsing telemetry)
PAGE_VIEW_EVENTS_SCHEMA: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["session_id", "path", "device", "timestamp"],
        "properties": {
            "user_id": {"bsonType": ["int", "null"], "description": "Authenticated user ID if logged in"},
            "session_id": {"bsonType": "string", "description": "Client session or cookie tracking ID"},
            "path": {"bsonType": "string", "description": "URL path requested"},
            "movie_id": {"bsonType": ["int", "null"], "description": "Target movie ID if browsing movie detail"},
            "device": {
                "enum": ["mobile", "desktop", "tablet"],
                "description": "Client device form factor",
            },
            "referrer": {"bsonType": ["string", "null"], "description": "HTTP Referrer header"},
            "timestamp": {"bsonType": "date", "description": "Event timestamp"},
        },
    }
}

# 3. Seat Selection Events (Cart / seat selection telemetry for abandonment analytics)
SEAT_SELECTION_EVENTS_SCHEMA: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["session_id", "show_id", "seat_ids", "action", "timestamp"],
        "properties": {
            "session_id": {"bsonType": "string", "description": "Client session identifier"},
            "user_id": {"bsonType": ["int", "null"], "description": "User ID if logged in"},
            "show_id": {"bsonType": "int", "description": "Target show ID"},
            "seat_ids": {
                "bsonType": "array",
                "items": {"bsonType": "int"},
                "description": "List of seat IDs involved in action",
            },
            "action": {
                "enum": ["select", "deselect", "abandon"],
                "description": "Seat action taken by moviegoer",
            },
            "timestamp": {"bsonType": "date", "description": "Event timestamp"},
        },
    }
}

# 4. Search Events (Query popularity & zero-result telemetry)
SEARCH_EVENTS_SCHEMA: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["query", "results_count", "timestamp"],
        "properties": {
            "query": {"bsonType": "string", "description": "Search query terms"},
            "results_count": {"bsonType": "int", "description": "Number of matching titles returned"},
            "user_id": {"bsonType": ["int", "null"], "description": "User ID if logged in"},
            "session_id": {"bsonType": ["string", "null"], "description": "Client session ID"},
            "timestamp": {"bsonType": "date", "description": "Event timestamp"},
        },
    }
}

# 5. Daily Revenue Summary (Pre-aggregated rollups refreshed by batch job)
DAILY_REVENUE_SUMMARY_SCHEMA: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["date", "date_str", "total_revenue", "total_bookings", "total_tickets", "updated_at"],
        "properties": {
            "date": {"bsonType": "date", "description": "Date truncated to midnight UTC"},
            "date_str": {"bsonType": "string", "description": "Date string YYYY-MM-DD"},
            "total_revenue": {"bsonType": ["double", "int", "decimal"], "description": "Aggregated revenue in INR"},
            "total_bookings": {"bsonType": "int", "description": "Total confirmed bookings count"},
            "total_tickets": {"bsonType": "int", "description": "Total tickets sold"},
            "by_format": {"bsonType": "array", "description": "Breakdown by audio/visual format"},
            "by_screen": {"bsonType": "array", "description": "Breakdown by auditorium"},
            "by_payment": {"bsonType": "array", "description": "Breakdown by payment method"},
            "updated_at": {"bsonType": "date", "description": "Last computation timestamp"},
        },
    }
}

# 6. Movie Performance Summary (Pre-aggregated rollups refreshed by batch job)
MOVIE_PERFORMANCE_SUMMARY_SCHEMA: Dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["movie_id", "movie_title", "total_revenue", "tickets_sold", "updated_at"],
        "properties": {
            "movie_id": {"bsonType": "int", "description": "SQL movie ID"},
            "movie_title": {"bsonType": "string", "description": "Movie title"},
            "genre": {"bsonType": "string", "description": "Movie genre"},
            "language": {"bsonType": "string", "description": "Movie language"},
            "total_revenue": {"bsonType": ["double", "int", "decimal"], "description": "Gross box office revenue"},
            "tickets_sold": {"bsonType": "int", "description": "Total tickets booked"},
            "cancellations_count": {"bsonType": "int", "description": "Total cancelled tickets"},
            "cancellation_rate": {"bsonType": ["double", "int"], "description": "Cancellation percentage"},
            "updated_at": {"bsonType": "date", "description": "Last computation timestamp"},
        },
    }
}

COLLECTION_SCHEMAS = {
    "booking_events": BOOKING_EVENTS_SCHEMA,
    "page_view_events": PAGE_VIEW_EVENTS_SCHEMA,
    "seat_selection_events": SEAT_SELECTION_EVENTS_SCHEMA,
    "search_events": SEARCH_EVENTS_SCHEMA,
    "daily_revenue_summary": DAILY_REVENUE_SUMMARY_SCHEMA,
    "movie_performance_summary": MOVIE_PERFORMANCE_SUMMARY_SCHEMA,
}


def apply_collection_schemas(db) -> None:
    """Create collections with validator or modify existing collections to enforce schema.
    
    Safe and idempotent on both standalone MongoDB and Replica Sets / Atlas.
    """
    if db is None:
        logger.warning("Cannot apply MongoDB schemas: database handle is None.")
        return

    try:
        existing_collections = db.list_collection_names()
    except Exception as exc:
        logger.warning("Could not list collections while applying schemas: %s", exc)
        return

    for coll_name, validator in COLLECTION_SCHEMAS.items():
        try:
            if coll_name not in existing_collections:
                db.create_collection(coll_name, validator=validator)
                logger.info("Created collection '%s' with JSON Schema validator.", coll_name)
            else:
                db.command("collMod", coll_name, validator=validator)
                logger.debug("Updated JSON Schema validator on collection '%s'.", coll_name)
        except Exception as exc:
            # mongomock or restricted Atlas user might not support collMod or validators
            logger.warning("Notice: Could not enforce schema validator on collection '%s': %s", coll_name, exc)
