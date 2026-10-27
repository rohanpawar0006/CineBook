import os
from flask import Flask, jsonify, render_template
from app.config import config_by_name
from app.extensions import db, login_manager, csrf, migrate
from app.extensions_mongo import mongo as mongo_ext


def create_app(config_name=None):
    """Application factory for CineBook."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # Ensure instance directory exists for SQLite
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    mongo_ext.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.movies import movies_bp
    from app.blueprints.booking import booking_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(movies_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)

    # Health check route
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "ok",
            "app": "CineBook",
            "version": "1.0.0"
        }), 200

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # Custom CLI command for seeding database
    @app.cli.command("seed")
    def seed_cli():
        """Seed initial demo data."""
        from seed import seed_database
        seed_database()

    @app.cli.command("init-mongo")
    def init_mongo_cli():
        """Initialize MongoDB collections, JSON Schema validators, and indexes."""
        from app.extensions_mongo import mongo as mongo_ext
        from app.mongo.schemas import apply_collection_schemas
        from app.mongo.indexes import create_indexes
        mongo_db = mongo_ext.get_db()
        if mongo_db is None:
            print("MongoDB is not reachable. Check MONGO_URI configuration.")
            return
        print(f"Applying schemas to MongoDB database: {mongo_db.name}...")
        apply_collection_schemas(mongo_db)
        print("Creating MongoDB indexes...")
        create_indexes(mongo_db)
        print("MongoDB initialized successfully.")

    @app.cli.command("sync-mongo")
    def sync_mongo_cli():
        """Idempotently sync existing SQL bookings into MongoDB booking_events."""
        from app.services.analytics_service import sync_sql_bookings_to_mongo
        print("Synchronizing SQL bookings to MongoDB booking_events...")
        synced = sync_sql_bookings_to_mongo()
        print(f"Sync complete: {synced} bookings synced.")

    @app.cli.command("refresh-summaries")
    def refresh_summaries_cli():
        """Rebuild MongoDB daily_revenue_summary and movie_performance_summary via $merge."""
        from app.mongo.jobs import run_summary_refresh_job
        print("Rebuilding pre-aggregated analytical summaries in MongoDB...")
        counts = run_summary_refresh_job()
        print(f"Summaries refreshed: {counts['daily_revenue']} daily revenue records, {counts['movie_performance']} movie performance records.")

    return app


# Module-level instance for WSGI servers expecting `app:app`
app = create_app(os.getenv("FLASK_ENV", "production"))

