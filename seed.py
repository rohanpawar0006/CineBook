import os
from datetime import datetime, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models import User, Movie, Screen, Seat, Show, Booking, BookingSeat


def seed_database():
    """Populate database with Indian cinema demo data (idempotent)."""
    app = create_app(os.getenv("FLASK_ENV", "development"))
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()

        # 1. Seed Users
        admin = User.query.filter_by(email="admin@cinebook.com").first()
        if not admin:
            admin = User(
                name="Cinema Manager (India)",
                email="admin@cinebook.com",
                role="admin"
            )
            admin.set_password("Admin@123")
            db.session.add(admin)
            print("Created admin user: admin@cinebook.com / Admin@123")

        test_user = User.query.filter_by(email="user@cinebook.com").first()
        if not test_user:
            test_user = User(
                name="Aarav Sharma",
                email="user@cinebook.com",
                role="user"
            )
            test_user.set_password("User@123")
            db.session.add(test_user)
            print("Created test user: user@cinebook.com / User@123")

        db.session.commit()

        # 2. Seed Screens & Seats
        screen1 = Screen.query.filter_by(name="Audi 1 — IMAX with Laser").first()
        if not screen1:
            screen1 = Screen(name="Audi 1 — IMAX with Laser", rows=8, cols=10)
            db.session.add(screen1)
            db.session.flush()

            # Rows A to H, Cols 1 to 10 (80 seats)
            row_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
            for r in row_labels:
                for c in range(1, 11):
                    seat = Seat(screen_id=screen1.id, row_label=r, number=c)
                    db.session.add(seat)
            print("Created Screen 1 (Audi 1 — IMAX with Laser) with 80 seats.")

        screen2 = Screen.query.filter_by(name="Audi 2 — Dolby Atmos 4K").first()
        if not screen2:
            screen2 = Screen(name="Audi 2 — Dolby Atmos 4K", rows=6, cols=8)
            db.session.add(screen2)
            db.session.flush()

            # Rows A to F, Cols 1 to 8 (48 seats)
            row_labels = ["A", "B", "C", "D", "E", "F"]
            for r in row_labels:
                for c in range(1, 9):
                    seat = Seat(screen_id=screen2.id, row_label=r, number=c)
                    db.session.add(seat)
            print("Created Screen 2 (Audi 2 — Dolby Atmos 4K) with 48 seats.")

        db.session.commit()

        # 3. Seed Indian Movies
        movies_data = [
            {
                "title": "Kalki 2898 AD",
                "description": "Set in a post-apocalyptic world in the year 2898 AD, a chosen warrior embarks on a mythological journey to protect an unborn child who is destined to be the Kalki avatar.",
                "language": "Hindi / Telugu",
                "genre": "Sci-Fi / Mythological Action",
                "duration_min": 181,
                "poster_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "Stree 2: Sarkate Ka Aatank",
                "description": "The town of Chanderi is haunted once again by a terrifying headless entity called Sarkata. Vicky and his gang must join forces with the mysterious Stree to save the town.",
                "language": "Hindi",
                "genre": "Horror / Comedy",
                "duration_min": 147,
                "poster_url": "https://images.unsplash.com/photo-1509347528160-9a9e33742cdb?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "RRR",
                "description": "A fearless revolutionary and an officer in the British force decide to join forces in 1920s India to fight against British tyrants in a battle of freedom and honor.",
                "language": "Telugu / Hindi",
                "genre": "Action / Epic Period Drama",
                "duration_min": 187,
                "poster_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "Jawan",
                "description": "A high-octane action thriller outlining the emotional journey of a prison warden committed to rectifying the wrongs in society and fulfilling a past promise.",
                "language": "Hindi / Tamil",
                "genre": "Action / Thriller",
                "duration_min": 169,
                "poster_url": "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "Manjummel Boys",
                "description": "A group of friends from a small town in Kerala embark on a leisure trip to Kodaikanal, where one of them gets trapped inside the perilous Guna Caves.",
                "language": "Malayalam / Tamil",
                "genre": "Survival / Adventure Drama",
                "duration_min": 135,
                "poster_url": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "Kantara",
                "description": "In a coastal village of Karnataka, a Kambala champion clashes with an upright forest officer while uncovering mystical divine traditions of Bhoota Kola.",
                "language": "Kannada / Hindi",
                "genre": "Action / Folklore Drama",
                "duration_min": 148,
                "poster_url": "https://images.unsplash.com/photo-1440404653325-ab127d49abc1?w=600&auto=format&fit=crop&q=80",
            },
        ]

        movies = []
        for m_data in movies_data:
            movie = Movie.query.filter_by(title=m_data["title"]).first()
            if not movie:
                movie = Movie(**m_data)
                db.session.add(movie)
                db.session.flush()
            movies.append(movie)
        db.session.commit()
        print(f"Ensured {len(movies)} Indian blockbuster movies in catalog.")

        # 4. Seed Shows in INR (₹)
        now = datetime.now(timezone.utc)
        # Indian multiplex ticket rates (₹180, ₹250, ₹320, ₹450)
        show_schedule = [
            (timedelta(hours=2), 350.00, screen1.id),
            (timedelta(hours=5), 450.00, screen1.id),
            (timedelta(hours=8), 280.00, screen2.id),
            (timedelta(days=1, hours=3), 220.00, screen1.id),
            (timedelta(days=1, hours=7), 350.00, screen2.id),
            (timedelta(days=2, hours=4), 250.00, screen1.id),
            (timedelta(days=2, hours=8), 420.00, screen2.id),
        ]

        # Reset shows if old shows exist without Indian screens
        Show.query.delete()
        db.session.commit()

        show_count = 0
        for idx, movie in enumerate(movies):
            time_offset, price, screen_id = show_schedule[idx % len(show_schedule)]
            start_dt = (now + time_offset).replace(minute=30, second=0, microsecond=0)
            show = Show(
                movie_id=movie.id,
                screen_id=screen_id,
                start_time=start_dt,
                price=price
            )
            db.session.add(show)
            show_count += 1

        db.session.commit()
        print(f"Created {show_count} upcoming Indian cinema shows in INR.")
        print("Database seeding completed successfully.")


if __name__ == "__main__":
    seed_database()
