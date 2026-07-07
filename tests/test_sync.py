"""Tests for sync service."""

from unittest.mock import patch, MagicMock
from webapp.sync import RedditSyncService, RedditAPIError, sync_user_items, unsave_user_item


def test_reddit_api_error():
    err = RedditAPIError("Token expired")
    assert str(err) == "Token expired"


def test_sync_service_init(app, user):
    config = {"REDDIT_USER_AGENT": "TestAgent/1.0"}
    service = RedditSyncService(user, config)
    assert service.user == user
    assert "Bearer" in service.headers["Authorization"]


def test_check_rate_limit(app, user):
    service = RedditSyncService(user, {})
    response = MagicMock()
    response.headers = {"x-ratelimit-remaining": "50", "x-ratelimit-reset": "10"}
    service._check_rate_limit(response)
    assert service.rate_limit_remaining == 50


def test_sync_user_items_user_not_found(app):
    result = sync_user_items(999)
    assert result["error"] == "User not found"


def test_sync_user_items_already_running(app, db, user):
    user.sync_in_progress = True
    db.session.commit()
    result = sync_user_items(user.id)
    assert result["error"] == "Sync already in progress"


def test_unsave_user_item_user_not_found(app):
    result = unsave_user_item(999, "abc")
    assert result["error"] == "User not found"


def test_unsave_user_item_item_not_found(app, user):
    result = unsave_user_item(user.id, "nonexistent")
    assert result["error"] == "Item not found"
