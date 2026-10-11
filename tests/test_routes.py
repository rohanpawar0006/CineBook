from datetime import datetime, timedelta, timezone
from app.extensions import db
from app.models import User, Movie, Screen, Seat, Show, Booking


def test_homepage_shows_movies(client, app):
    """Test that the homepage lists active movies."""
    with app.app_context():
        movie = Movie(
            title="Inception",
            description="Dream inside a dream",
            language="English",
            genre="Action",
            duration_min=148
        )
        db.session.add(movie)
        db.session.commit()

    response = client.get("/")
    assert response.status_code == 200
    assert b"Inception" in response.data
    assert b"Now Showing" in response.data


def test_movie_detail_and_404(client, app):
    """Test movie details view and 404 on missing movie."""
    with app.app_context():
        movie = Movie(
            title="Interstellar",
            description="Space travel",
            language="English",
            genre="Sci-Fi",
            duration_min=169
        )
        db.session.add(movie)
        db.session.commit()
        movie_id = movie.id

    res_ok = client.get(f"/movies/{movie_id}")
    assert res_ok.status_code == 200
    assert b"Interstellar" in res_ok.data

    res_missing = client.get("/movies/99999")
    assert res_missing.status_code == 404
    assert b"Page Not Found" in res_missing.data


def test_auth_signup_and_login_flow(client, app):
    """Test signup, login, and logout flow."""
    # 1. Sign up
    signup_res = client.post("/signup", data={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "Password123",
        "confirm_password": "Password123"
    }, follow_redirects=True)
    assert signup_res.status_code == 200
    assert b"Your account has been created!" in signup_res.data

    # 2. Duplicate signup fails
    dup_res = client.post("/signup", data={
        "name": "Jane Dup",
        "email": "jane@example.com",
        "password": "Password123",
        "confirm_password": "Password123"
    })
    assert b"This email address is already registered." in dup_res.data

    # 3. Log in with wrong password fails
    wrong_login = client.post("/login", data={
        "email": "jane@example.com",
        "password": "WrongPassword"
    }, follow_redirects=True)
    assert b"Invalid email or password." in wrong_login.data

    # 4. Log in successfully
    login_res = client.post("/login", data={
        "email": "jane@example.com",
        "password": "Password123"
    }, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Hi, Jane Doe" in login_res.data

    # 5. Logout
    logout_res = client.post("/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"You have been logged out" in logout_res.data


def test_booking_flow_end_to_end(client, app):
    """Test end to end user booking and cancellation flow."""
    with app.app_context():
        user = User(name="Bob Tester", email="bob@test.com")
        user.set_password("Pass123")
        screen = Screen(name="Screen 1", rows=2, cols=2)
        movie = Movie(
            title="Dunkirk",
            description="War drama",
            language="English",
            genre="War",
            duration_min=106
        )
        db.session.add_all([user, screen, movie])
        db.session.commit()

        s1 = Seat(screen_id=screen.id, row_label="A", number=1)
        s2 = Seat(screen_id=screen.id, row_label="A", number=2)
        show = Show(
            movie_id=movie.id,
            screen_id=screen.id,
            start_time=datetime.now(timezone.utc) + timedelta(hours=3),
            price=15.00
        )
        db.session.add_all([s1, s2, show])
        db.session.commit()

        show_id = show.id
        seat_id = s1.id

    # Unauthenticated user redirected
    anon_res = client.get(f"/shows/{show_id}/seats")
    assert anon_res.status_code == 302
    assert "/login" in anon_res.headers["Location"]

    # Log in as Bob
    client.post("/login", data={"email": "bob@test.com", "password": "Pass123"})

    # Check seat map page and API
    map_res = client.get(f"/shows/{show_id}/seats")
    assert map_res.status_code == 200
    assert b"Dunkirk" in map_res.data

    api_res = client.get(f"/api/shows/{show_id}/seats")
    assert api_res.status_code == 200
    json_data = api_res.get_json()
    assert json_data["movie_title"] == "Dunkirk"
    assert len(json_data["seats"]) == 2

    # Book seat
    book_res = client.post(f"/shows/{show_id}/book", data={"seat_ids": str(seat_id)}, follow_redirects=True)
    assert book_res.status_code == 200
    assert b"Booking confirmed!" in book_res.data
    assert b"Your Tickets Are Ready!" in book_res.data

    # Check My Bookings page
    my_res = client.get("/bookings")
    assert my_res.status_code == 200
    assert b"Dunkirk" in my_res.data
    assert b"CONFIRMED" in my_res.data

    # Cancel the booking
    with app.app_context():
        booking = Booking.query.filter_by(show_id=show_id).first()
        booking_id = booking.id

    cancel_res = client.post(f"/bookings/{booking_id}/cancel", follow_redirects=True)
    assert cancel_res.status_code == 200
    assert b"Your booking has been cancelled" in cancel_res.data


def test_admin_access_control_and_management(client, app):
    """Test admin role security and management routes."""
    with app.app_context():
        regular_user = User(name="Regular", email="reg@test.com", role="user")
        regular_user.set_password("RegPass1")
        admin_user = User(name="Manager", email="admin@test.com", role="admin")
        admin_user.set_password("AdminPass1")
        screen = Screen(name="Screen 1", rows=5, cols=5)
        db.session.add_all([regular_user, admin_user, screen])
        db.session.commit()

    # Regular user gets 403 Forbidden on /admin
    client.post("/login", data={"email": "reg@test.com", "password": "RegPass1"})
    forbidden_res = client.get("/admin")
    assert forbidden_res.status_code == 403
    assert b"Access Restricted" in forbidden_res.data
    client.post("/logout")

    # Admin user gets 200 on /admin
    client.post("/login", data={"email": "admin@test.com", "password": "AdminPass1"})
    admin_res = client.get("/admin")
    assert admin_res.status_code == 200
    assert b"Cinema Management Dashboard" in admin_res.data

    # Admin adds new movie
    add_movie_res = client.post("/admin/movies/new", data={
        "title": "Gladiator II",
        "description": "Colosseum action",
        "language": "English",
        "genre": "Action / Adventure",
        "duration_min": "148",
        "poster_url": ""
    }, follow_redirects=True)
    assert add_movie_res.status_code == 200
    assert b"Gladiator II" in add_movie_res.data
