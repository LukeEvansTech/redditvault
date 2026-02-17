"""Shared test fixtures."""

import pytest
from datetime import datetime, timedelta
from webapp.app import create_app
from webapp.extensions import db as _db
from webapp.models import User, SavedItem, ApiKey
from webapp.api_auth import generate_api_key


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"
    REDDIT_CLIENT_ID = "test-client-id"
    REDDIT_CLIENT_SECRET = "test-client-secret"
    REDDIT_REDIRECT_URI = "http://localhost:5000/auth/callback"
    REDDIT_USER_AGENT = "TestAgent/1.0"
    REDDIT_SCOPES = ("identity", "history", "read", "save")
    REDIS_URL = "redis://localhost:6379/0"
    WTF_CSRF_ENABLED = False


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app, db):
    u = User(
        reddit_id="test123",
        username="testuser",
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        token_expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def saved_item(app, db, user):
    item = SavedItem(
        user_id=user.id,
        reddit_id="abc123",
        reddit_fullname="t3_abc123",
        item_type="post",
        subreddit="homelab",
        author="testauthor",
        permalink="https://reddit.com/r/homelab/comments/abc123",
        score=42,
        created_utc=datetime.utcnow(),
        title="Test Post Title",
        category="Self-Hosting & Homelab",
    )
    db.session.add(item)
    db.session.commit()
    return item


@pytest.fixture
def api_key(app, db, user):
    raw_key, key_hash = generate_api_key()
    key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        name="test-key",
    )
    db.session.add(key)
    db.session.commit()
    return raw_key, key


@pytest.fixture
def auth_client(client, user):
    """Client with authenticated session."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
    return client
