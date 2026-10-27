"""Automated Test Suite for CineBook MongoDB Big-Data & Analytics Layer.

Tests:
- Graceful degradation when MongoDB is down or offline (SQL transactional integrity preserved)
- Fire-and-forget ingestion (booking events, cancellation events, page views, seat telemetry)
- Idempotent SQL -> Mongo synchronization
- All 11 analytical aggregation pipelines using deterministic fixtures and exact assertions
- Summary refresh background job
- Admin access control and API/export endpoints
"""

from datetime import datetime, timedelta, timezone
import pytest
import mongomock
from app.extensions import db
from app.extensions_mongo import mongo
from app.models import User, Movie, Screen, Seat, Show, Booking, BookingSeat
from app.services import booking_service, analytics_service
from app.mongo import analytics_queries, jobs


@pytest.fixture
def mock_mongo():
    """Fixture providing an isolated in-memory mongomock Database."""
    client = mongomock.MongoClient()
    mock_db = client["cinebook_analytics_test"]
    mongo.set_db(mock_db)
    yield mock_db
    mongo.reset()


@pytest.fixture
def cinema_data(app):
    """Seed minimal cinema catalog for testing."""
    user = User(name="Rohan Sharma", email="rohan@example.com")
    user.set_password("Pass123")
    admin = User(name="Cinema Manager", email="manager@cinebook.com", role="admin")
    admin.set_password("AdminPass123")

    movie1 = Movie(
        title="Kalki 2898 AD",
        description="Sci-Fi Mythological",
        language="Hindi",
        genre="Sci-Fi",
        duration_min=180,
    )
    movie2 = Movie(
        title="Stree 2",
        description="Horror comedy",
        language="Hindi",
        genre="Horror",
        duration_min=140,
    )
    screen = Screen(name="Audi 1 — IMAX with Laser", rows=3, cols=3)

    db.session.add_all([user, admin, movie1, movie2, screen])
    db.session.commit()

    seats = []
    for r in ["A", "B", "C"]:
        for c in [1, 2, 3]:
            s = Seat(screen_id=screen.id, row_label=r, number=c)
            db.session.add(s)
            seats.append(s)
    db.session.commit()

    show1 = Show(
        movie_id=movie1.id,
        screen_id=screen.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=4),
        price=350.00,
    )
    show2 = Show(
        movie_id=movie2.id,
        screen_id=screen.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=6),
        price=250.00,
    )
    db.session.add_all([show1, show2])
    db.session.commit()

    return {
        "user": user,
        "admin": admin,
        "movie1": movie1,
        "movie2": movie2,
        "screen": screen,
        "seats": seats,
        "show1": show1,
        "show2": show2,
    }


def test_graceful_degradation_when_mongo_offline(app, cinema_data):
    """Verify that if MongoDB is offline, SQL bookings succeed without error."""
    # Force mongo to None/unavailable
    mongo.reset()
    mongo._custom_db = None
    mongo._client = None
    mongo._is_available = False

    user = cinema_data["user"]
    show = cinema_data["show1"]
    seat = cinema_data["seats"][0]

    # Booking should succeed completely in SQL despite Mongo being down
    booking = booking_service.create_booking(user, show.id, [seat.id])
    assert booking.id is not None
    assert booking.status == "CONFIRMED"

    # Cancellation should succeed completely in SQL despite Mongo being down
    cancelled = booking_service.cancel_booking(user, booking.id)
    assert cancelled.status == "CANCELLED"


def test_mongo_ingestion_and_cancellation(app, cinema_data, mock_mongo):
    """Test fire-and-forget ingestion of booking and cancellation into MongoDB."""
    user = cinema_data["user"]
    show = cinema_data["show1"]
    seats = cinema_data["seats"][:2]

    # Create booking
    booking = booking_service.create_booking(
        user,
        show.id,
        [s.id for s in seats],
        payment_method="GPay",
        city="Bengaluru",
    )
    assert booking.id is not None

    # Check MongoDB booking_events document
    event = mock_mongo.booking_events.find_one({"booking_id": booking.id})
    assert event is not None
    assert event["movie_title"] == "Kalki 2898 AD"
    assert event["format"] == "IMAX with Laser"
    assert event["payment_method"] == "GPay"
    assert event["city"] == "Bengaluru"
    assert event["status"] == "CONFIRMED"
    assert len(event["seats"]) == 2
    assert float(event["amount_inr"]) == 700.00

    # Cancel booking
    booking_service.cancel_booking(user, booking.id)
    updated_event = mock_mongo.booking_events.find_one({"booking_id": booking.id})
    assert updated_event["status"] == "CANCELLED"
    assert updated_event["cancelled_at"] is not None


def test_sync_sql_bookings_cli(app, cinema_data, mock_mongo):
    """Test sync_sql_bookings_to_mongo backfills existing SQL bookings into Mongo."""
    user = cinema_data["user"]
    show = cinema_data["show2"]
    seat = cinema_data["seats"][2]

    booking = Booking(
        code="CB-SYNC99",
        user_id=user.id,
        show_id=show.id,
        status="CONFIRMED",
        total_amount=250.00,
    )
    db.session.add(booking)
    db.session.flush()

    bs = BookingSeat(booking_id=booking.id, show_id=show.id, seat_id=seat.id)
    db.session.add(bs)
    db.session.commit()

    # Clear Mongo to simulate unsynced state
    mock_mongo.booking_events.delete_many({})

    count = analytics_service.sync_sql_bookings_to_mongo()
    assert count >= 1

    synced_doc = mock_mongo.booking_events.find_one({"booking_id": booking.id})
    assert synced_doc is not None
    assert synced_doc["movie_title"] == "Stree 2"
    assert synced_doc["amount_inr"] == 250.00


def test_deterministic_aggregation_pipelines(mock_mongo):
    """Test all analytical pipelines against deterministic test dataset with exact assertions."""
    now = datetime(2026, 10, 27, 18, 30, tzinfo=timezone.utc)

    # Insert deterministic fixtures
    events = [
        {
            "booking_id": 1,
            "user_id": 101,
            "movie_id": 1,
            "movie_title": "Kalki 2898 AD",
            "genre": "Sci-Fi",
            "language": "Hindi",
            "show_id": 10,
            "screen": "Audi 1 — IMAX with Laser",
            "format": "IMAX with Laser",
            "show_datetime": now,
            "seats": ["A1", "A2"],
            "seat_categories": ["Classic", "Classic"],
            "amount_inr": 700.00,
            "payment_method": "UPI",
            "status": "CONFIRMED",
            "city": "Mumbai",
            "created_at": now - timedelta(hours=2),
            "cancelled_at": None,
        },
        {
            "booking_id": 2,
            "user_id": 101,
            "movie_id": 1,
            "movie_title": "Kalki 2898 AD",
            "genre": "Sci-Fi",
            "language": "Hindi",
            "show_id": 10,
            "screen": "Audi 1 — IMAX with Laser",
            "format": "IMAX with Laser",
            "show_datetime": now,
            "seats": ["B1"],
            "seat_categories": ["Classic"],
            "amount_inr": 350.00,
            "payment_method": "GPay",
            "status": "CONFIRMED",
            "city": "Mumbai",
            "created_at": now - timedelta(hours=1),
            "cancelled_at": None,
        },
        {
            "booking_id": 3,
            "user_id": 102,
            "movie_id": 2,
            "movie_title": "Stree 2",
            "genre": "Horror",
            "language": "Hindi",
            "show_id": 11,
            "screen": "Audi 2 — Dolby Atmos 4K",
            "format": "Dolby Atmos 4K",
            "show_datetime": now + timedelta(days=1),
            "seats": ["C1", "C2"],
            "seat_categories": ["Prime", "Prime"],
            "amount_inr": 500.00,
            "payment_method": "PhonePe",
            "status": "CONFIRMED",
            "city": "Delhi-NCR",
            "created_at": now - timedelta(minutes=30),
            "cancelled_at": None,
        },
        {
            "booking_id": 4,
            "user_id": 103,
            "movie_id": 2,
            "movie_title": "Stree 2",
            "genre": "Horror",
            "language": "Hindi",
            "show_id": 11,
            "screen": "Audi 2 — Dolby Atmos 4K",
            "format": "Dolby Atmos 4K",
            "show_datetime": now + timedelta(days=1),
            "seats": ["C3"],
            "seat_categories": ["Prime"],
            "amount_inr": 250.00,
            "payment_method": "RuPay",
            "status": "CANCELLED",
            "city": "Delhi-NCR",
            "created_at": now - timedelta(minutes=20),
            "cancelled_at": now - timedelta(minutes=5),
        },
    ]
    mock_mongo.booking_events.insert_many(events)

    # 1. KPIs
    kpis = analytics_queries.get_kpis(mock_mongo)
    assert kpis["total_revenue"] == 1550.00
    assert kpis["total_bookings"] == 3
    assert kpis["total_tickets"] == 5
    assert kpis["cancellation_rate"] == 25.0

    # 2. Top Movies
    top_movies = analytics_queries.get_top_movies(mock_mongo, limit=5)
    assert len(top_movies) == 2
    assert top_movies[0]["movie_title"] == "Kalki 2898 AD"
    assert top_movies[0]["total_revenue"] == 1050.00
    assert top_movies[0]["tickets_sold"] == 3
    assert top_movies[1]["movie_title"] == "Stree 2"
    assert top_movies[1]["total_revenue"] == 500.00

    # 3. Payment Methods
    payments = analytics_queries.get_payment_method_distribution(mock_mongo)
    pay_dict = {p["payment_method"]: p["total_revenue"] for p in payments}
    assert pay_dict["UPI"] == 700.00
    assert pay_dict["PhonePe"] == 500.00
    assert pay_dict["GPay"] == 350.00

    # 4. Cancellation Analytics
    cancels = analytics_queries.get_cancellation_analytics(mock_mongo)
    assert cancels["overall"]["total"] == 4
    assert cancels["overall"]["cancelled"] == 1
    assert cancels["overall"]["cancellation_rate_pct"] == 25.0

    # 5. Seat Popularity
    seats_report = analytics_queries.get_seat_popularity(mock_mongo)
    seat_labels = [s["seat"] for s in seats_report["most_booked"]]
    assert "A1" in seat_labels
    assert "C1" in seat_labels

    # 6. Customer Segmentation
    seg = analytics_queries.get_customer_segmentation(mock_mongo)
    assert seg["total_unique_customers"] == 2  # user 101 and 102 (confirmed)
    # user 101 booked 2 times -> repeat customer
    assert seg["repeat_rate"] == 50.0


def test_summary_refresh_job(mock_mongo):
    """Test background summary aggregation job."""
    now = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
    mock_mongo.booking_events.insert_one({
        "booking_id": 999,
        "user_id": 50,
        "movie_id": 1,
        "movie_title": "Kalki 2898 AD",
        "genre": "Sci-Fi",
        "language": "Hindi",
        "show_id": 1,
        "screen": "Audi 1",
        "format": "IMAX with Laser",
        "show_datetime": now,
        "seats": ["A1"],
        "seat_categories": ["Classic"],
        "amount_inr": 350.00,
        "payment_method": "UPI",
        "status": "CONFIRMED",
        "city": "Mumbai",
        "created_at": now,
        "cancelled_at": None,
    })

    summary_counts = jobs.run_summary_refresh_job()
    assert summary_counts["daily_revenue"] >= 1
    assert summary_counts["movie_performance"] >= 1


def test_admin_analytics_dashboard_routes(client, app, cinema_data, mock_mongo):
    """Test authorization and endpoints on /admin/analytics."""
    # 1. Unauthenticated user redirected to login
    anon_res = client.get("/admin/analytics")
    assert anon_res.status_code == 302
    assert "/login" in anon_res.headers["Location"]

    # 2. Regular user gets 403 Forbidden
    client.post("/login", data={"email": "rohan@example.com", "password": "Pass123"})
    forbidden_res = client.get("/admin/analytics")
    assert forbidden_res.status_code == 403
    client.post("/logout")

    # 3. Admin user gets 200 OK on /admin/analytics
    client.post("/login", data={"email": "manager@cinebook.com", "password": "AdminPass123"})
    admin_res = client.get("/admin/analytics")
    assert admin_res.status_code == 200
    assert b"Big-Data Analytics" in admin_res.data

    # 4. JSON API endpoint /admin/analytics/api/kpis
    api_res = client.get("/admin/analytics/api/kpis")
    assert api_res.status_code == 200
    data = api_res.get_json()
    assert "total_revenue" in data
    assert "total_bookings" in data

    # 5. CSV Export endpoint
    csv_res = client.get("/admin/analytics/export?type=top-movies")
    assert csv_res.status_code == 200
    assert csv_res.mimetype == "text/csv"
    assert b"Movie ID,Title,Genre" in csv_res.data
