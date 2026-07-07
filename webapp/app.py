#!/usr/bin/env python3
"""Web UI for browsing Reddit saved items."""

import os

from flask import Flask
from .config import Config
from .extensions import db, login_manager
from .models import User
from .auth import auth_bp
from .views import views_bp
from .api import api_bp


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    # Create database tables (handled gracefully for multi-worker setup)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.debug("Database tables may already exist: %s", e)

    return app


# For gunicorn: create_app() returns the app
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
