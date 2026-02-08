"""Flask application configuration."""

import os
from datetime import timedelta


class Config:
    """Application configuration from environment variables."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32)

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///reddit_saved.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Reddit OAuth
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
    REDDIT_REDIRECT_URI = os.environ.get("REDDIT_REDIRECT_URI", "http://localhost:5000/auth/callback")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "RedditSavedViewer/1.0")
    REDDIT_SCOPES = ["identity", "history", "read", "save"]

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # Redis/Dragonfly for RQ
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
