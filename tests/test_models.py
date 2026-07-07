"""Tests for database models."""

from datetime import datetime, timedelta
from webapp.models import User, SavedItem, ApiKey


def test_user_creation(app, db):
    user = User(reddit_id="u1", username="alice")
    db.session.add(user)
    db.session.commit()
    assert user.id is not None
    assert user.username == "alice"
    assert user.sync_in_progress is False


def test_user_is_token_expired_no_expiry(user):
    user.token_expires_at = None
    assert user.is_token_expired() is True


def test_user_is_token_expired_future(user):
    user.token_expires_at = datetime.utcnow() + timedelta(hours=1)
    assert user.is_token_expired() is False


def test_user_is_token_expired_past(user):
    user.token_expires_at = datetime.utcnow() - timedelta(minutes=1)
    assert user.is_token_expired() is True


def test_user_is_token_expired_within_buffer(user):
    user.token_expires_at = datetime.utcnow() + timedelta(minutes=3)
    assert user.is_token_expired() is True


def test_saved_item_creation(saved_item):
    assert saved_item.id is not None
    assert saved_item.item_type == "post"
    assert saved_item.subreddit == "homelab"
    assert saved_item.reviewed is False


def test_saved_item_unique_constraint(app, db, user):
    item1 = SavedItem(
        user_id=user.id, reddit_id="dup1", reddit_fullname="t3_dup1",
        item_type="post", subreddit="test", author="a",
        permalink="https://reddit.com/test", score=1,
        created_utc=datetime.utcnow(),
    )
    db.session.add(item1)
    db.session.commit()

    import sqlalchemy
    item2 = SavedItem(
        user_id=user.id, reddit_id="dup1", reddit_fullname="t3_dup1",
        item_type="post", subreddit="test", author="a",
        permalink="https://reddit.com/test", score=1,
        created_utc=datetime.utcnow(),
    )
    db.session.add(item2)
    try:
        db.session.commit()
        assert False, "Should have raised IntegrityError"
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()


def test_api_key_creation(app, db, user):
    key = ApiKey(user_id=user.id, key_hash="abc123hash", name="my-key")
    db.session.add(key)
    db.session.commit()
    assert key.is_active is True
    assert key.last_used_at is None
