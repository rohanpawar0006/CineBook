import os
from datetime import datetime, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models import User, Movie, Screen, Seat, Show, Booking, BookingSeat


def seed_database():
    """Populate database with demo data (idempotent)."""
    app = create_app(os.getenv("FLASK_ENV", "development"))
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()

        # 1. Seed Users
        admin = User.query.filter_by(email="admin@cinebook.com").first()
        if not admin:
            admin = User(
                name="Cinema Manager",
                email="admin@cinebook.com",
                role="admin"
            )
            admin.set_password("Admin@123")
            db.session.add(admin)
            print("Created admin user: admin@cinebook.com / Admin@123")

        test_user = User.query.filter_by(email="user@cinebook.com").first()
        if not test_user:
            test_user = User(
                name="John Doe",
                email="user@cinebook.com",
                role="user"
            )
            test_user.set_password("User@123")
            db.session.add(test_user)
            print("Created test user: user@cinebook.com / User@123")

        db.session.commit()

        # 2. Seed Screens & Seats
        screen1 = Screen.query.filter_by(name="Audi 1 (IMAX)").first()
        if not screen1:
            screen1 = Screen(name="Audi 1 (IMAX)", rows=8, cols=10)
            db.session.add(screen1)
            db.session.flush()

            # Rows A to H, Cols 1 to 10 (80 seats)
            row_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
            for r in row_labels:
                for c in range(1, 11):
                    seat = Seat(screen_id=screen1.id, row_label=r, number=c)
                    db.session.add(seat)
            print("Created Screen 1 with 80 seats.")

        screen2 = Screen.query.filter_by(name="Audi 2 (Dolby Atmos)").first()
        if not screen2:
            screen2 = Screen(name="Audi 2 (Dolby Atmos)", rows=6, cols=8)
            db.session.add(screen2)
            db.session.flush()

            # Rows A to F, Cols 1 to 8 (48 seats)
            row_labels = ["A", "B", "C", "D", "E", "F"]
            for r in row_labels:
                for c in range(1, 9):
                    seat = Seat(screen_id=screen2.id, row_label=r, number=c)
                    db.session.add(seat)
            print("Created Screen 2 with 48 seats.")

        db.session.commit()

        # 3. Seed Movies
        movies_data = [
            {
                "title": "Interstellar",
                "description": "When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot, Joseph Cooper, is tasked to pilot a spacecraft, along with a team of researchers, to find a new planet for humans.",
                "language": "English",
                "genre": "Sci-Fi / Adventure",
                "duration_min": 169,
                "poster_url": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "Inception",
                "description": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
                "language": "English",
                "genre": "Action / Sci-Fi",
                "duration_min": 148,
                "poster_url": "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "The Dark Knight",
                "description": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
                "language": "English",
                "genre": "Action / Crime / Drama",
                "duration_min": 152,
                "poster_url": "https://images.unsplash.com/photo-1509347528160-9a9e33742cdb?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "Spirited Away",
                "description": "During her family's move to the suburbs, a sullen 10-year-old girl wanders into a world ruled by gods, witches, and spirits, and where humans are changed into beasts.",
                "language": "Japanese",
                "genre": "Animation / Fantasy",
                "duration_min": 125,
                "poster_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "Parasite",
                "description": "Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.",
                "language": "Korean",
                "genre": "Drama / Thriller",
                "duration_min": 132,
                "poster_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=600&auto=format&fit=crop&q=80",
            },
            {
                "title": "Oppenheimer",
                "description": "The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb during World War II.",
                "language": "English",
                "genre": "Biography / Drama",
                "duration_min": 180,
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
        print(f"Ensured {len(movies)} movies in catalog.")

        # 4. Seed Shows
        now = datetime.now(timezone.utc)
        # Generate upcoming shows over the next 3 days
        if Show.query.count() == 0:
            show_times = [
                (timedelta(hours=2), 12.50, screen1.id),
                (timedelta(hours=5), 14.00, screen1.id),
                (timedelta(hours=8), 16.50, screen2.id),
                (timedelta(days=1, hours=3), 12.50, screen1.id),
                (timedelta(days=1, hours=7), 15.00, screen2.id),
                (timedelta(days=2, hours=4), 13.00, screen1.id),
                (timedelta(days=2, hours=8), 16.50, screen2.id),
            ]

            show_count = 0
            for idx, movie in enumerate(movies):
                time_offset, price, screen_id = show_times[idx % len(show_times)]
                start_dt = (now + time_offset).replace(minute=0, second=0, microsecond=0)
                show = Show(
                    movie_id=movie.id,
                    screen_id=screen_id,
                    start_time=start_dt,
                    price=price
                )
                db.session.add(show)
                show_count += 1

            db.session.commit()
            print(f"Created {show_count} upcoming shows.")

        print("Database seeding completed successfully.")


if __name__ == "__main__":
    seed_database()
