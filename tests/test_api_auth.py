"""Tests for API key authentication."""

from webapp.api_auth import generate_api_key, verify_api_key


def test_generate_api_key():
    raw_key, key_hash = generate_api_key()
    assert len(raw_key) == 64  # 32 bytes hex
    assert len(key_hash) == 64  # SHA-256 hex digest
    assert raw_key != key_hash


def test_verify_api_key_valid(app, api_key):
    raw_key, key_obj = api_key
    user = verify_api_key(raw_key)
    assert user is not None
    assert user.username == "testuser"


def test_verify_api_key_invalid(app):
    user = verify_api_key("nonexistent-key")
    assert user is None


def test_verify_api_key_inactive(app, db, api_key):
    raw_key, key_obj = api_key
    key_obj.is_active = False
    db.session.commit()
    user = verify_api_key(raw_key)
    assert user is None
