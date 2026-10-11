import os
from flask import Flask, jsonify, render_template
from app.config import config_by_name
from app.extensions import db, login_manager, csrf, migrate


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

    return app


# Module-level instance for WSGI servers expecting `app:app`
app = create_app(os.getenv("FLASK_ENV", "production"))

