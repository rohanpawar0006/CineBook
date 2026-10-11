import os
from app import create_app
from app.extensions import db

# Create WSGI application instance
app = create_app(os.getenv("FLASK_ENV", "production"))

# Auto-initialize database tables and seed data on startup if empty
with app.app_context():
    db.create_all()
    try:
        from app.models import Movie
        if Movie.query.count() == 0:
            print("Database empty: Auto-seeding Indian cinema catalog...")
            from seed import seed_database
            seed_database()
            print("Auto-seeding complete.")
    except Exception as err:
        print("Notice during auto-seed check:", err)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
