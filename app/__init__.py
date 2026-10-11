import os
from flask import Flask, jsonify
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

    # Health check route for Phase 0
    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "ok",
            "app": "CineBook",
            "version": "0.1.0"
        }), 200

    return app
