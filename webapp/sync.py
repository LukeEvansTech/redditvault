"""Reddit saved items sync service."""

import time
import requests
from datetime import datetime
from flask import current_app
from .extensions import db
from .models import User, SavedItem
from .categories import categorize_subreddit


class RedditAPIError(Exception):
    """Custom exception for Reddit API errors."""
    pass


class RedditSyncService:
    """Service for syncing saved items from Reddit."""

    BASE_URL = "https://oauth.reddit.com"

    def __init__(self, user: User, config: dict):
        self.user = user
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {user.access_token}",
            "User-Agent": config.get("REDDIT_USER_AGENT", "RedditSavedViewer/1.0"),
        }
        self.rate_limit_remaining = 60
        self.rate_limit_reset = 0

    def _check_rate_limit(self, response):
        """Update rate limit tracking from response headers."""
        self.rate_limit_remaining = int(float(response.headers.get("x-ratelimit-remaining", 60)))
        self.rate_limit_reset = float(response.headers.get("x-ratelimit-reset", 0))

        if self.rate_limit_remaining < 5:
            sleep_time = max(self.rate_limit_reset, 1)
            time.sleep(sleep_time)

    def _make_request(self, endpoint: str, params: dict = None, method: str = "GET", data: dict = None) -> dict:
        """Make rate-limited request to Reddit API."""
        url = f"{self.BASE_URL}{endpoint}"

        if method == "POST":
            response = requests.post(url, headers=self.headers, data=data, timeout=30)
        else:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)

        self._check_rate_limit(response)

        if response.status_code == 401:
            raise RedditAPIError("Token expired")
        elif response.status_code == 429:
            time.sleep(60)
            return self._make_request(endpoint, params, method, data)
        elif response.status_code not in (200, 202):
            raise RedditAPIError(f"API error: {response.status_code}")

        # Some endpoints return empty response
        if response.text:
            return response.json()
        return {}

    def sync_saved_items(self, full_sync: bool = False) -> tuple[int, int]:
        """
        Sync saved items from Reddit.

        Args:
            full_sync: If True, fetch all items. If False, stop at first known item.

        Returns:
            Tuple of (new_count, updated_count)
        """
        new_count = 0
        updated_count = 0
        after = None

        while True:
            params = {"limit": 100}
            if after:
                params["after"] = after

            data = self._make_request(f"/user/{self.user.username}/saved", params)

            items = data.get("data", {}).get("children", [])

            if not items:
                break

            for item_data in items:
                kind = item_data["kind"]  # t3 = post, t1 = comment
                item = item_data["data"]

                existing = SavedItem.query.filter_by(
                    user_id=self.user.id,
                    reddit_id=item["id"]
                ).first()

                if existing:
                    if not full_sync:
                        continue
                    self._update_item(existing, item, kind)
                    updated_count += 1
                else:
                    self._create_item(item, kind)
                    new_count += 1

            after = data.get("data", {}).get("after")
            if not after:
                break

            time.sleep(0.5)

        self.user.last_sync_at = datetime.utcnow()
        self.user.sync_in_progress = False
        db.session.commit()

        return new_count, updated_count

    def _create_item(self, item: dict, kind: str):
        """Create a new SavedItem from Reddit data."""
        is_post = kind == "t3"

        saved_item = SavedItem(
            user_id=self.user.id,
            reddit_id=item["id"],
            reddit_fullname=item["name"],
            item_type="post" if is_post else "comment",
            subreddit=item["subreddit"],
            author=item.get("author", "[deleted]"),
            permalink=f"https://reddit.com{item['permalink']}",
            score=int(float(item.get("score", 0) or 0)),
            created_utc=datetime.utcfromtimestamp(item["created_utc"]),
            category=categorize_subreddit(item["subreddit"]),
        )

        if is_post:
            saved_item.title = item.get("title")
            saved_item.url = item.get("url")
            selftext = item.get("selftext") or ""
            saved_item.selftext = selftext[:2000] if selftext else None
            saved_item.is_self = item.get("is_self")
            saved_item.num_comments = int(float(item.get("num_comments") or 0)) if item.get("num_comments") is not None else None
        else:
            body = item.get("body") or ""
            saved_item.body = body[:2000] if body else None
            saved_item.post_title = item.get("link_title")

        db.session.add(saved_item)
        db.session.commit()

    def _update_item(self, existing: SavedItem, item: dict, kind: str):
        """Update an existing SavedItem."""
        existing.score = int(float(item.get("score", existing.score) or 0))
        existing.synced_at = datetime.utcnow()

        if kind == "t3":
            nc = item.get("num_comments")
            if nc is not None:
                existing.num_comments = int(float(nc))

        db.session.commit()

    def unsave_item(self, fullname: str) -> bool:
        """
        Unsave an item on Reddit.

        Args:
            fullname: Reddit fullname (e.g., t3_abc123 or t1_xyz789)

        Returns:
            True if successful
        """
        self._make_request("/api/unsave", method="POST", data={"id": fullname})
        return True


def sync_user_items(user_id: int, full_sync: bool = False) -> dict:
    """
    Sync saved items for a user. Can be called directly or queued via RQ.

    Args:
        user_id: The user's database ID
        full_sync: Whether to do a full sync or incremental

    Returns:
        Dict with status and counts
    """
    from flask import current_app

    user = User.query.get(user_id)

    if not user:
        return {"error": "User not found"}

    if user.sync_in_progress:
        return {"error": "Sync already in progress"}

    user.sync_in_progress = True
    db.session.commit()

    try:
        # Check if token needs refresh
        if user.is_token_expired():
            from .auth import refresh_access_token
            if not refresh_access_token(user):
                user.sync_in_progress = False
                db.session.commit()
                return {"error": "Token refresh failed"}

        sync_service = RedditSyncService(user, current_app.config)
        new_count, updated_count = sync_service.sync_saved_items(full_sync)

        return {
            "status": "success",
            "new_items": new_count,
            "updated_items": updated_count,
        }

    except RedditAPIError as e:
        user.sync_in_progress = False
        db.session.commit()
        return {"error": str(e)}

    except Exception as e:
        user.sync_in_progress = False
        db.session.commit()
        current_app.logger.error(f"Sync error for user {user_id}: {e}")
        return {"error": str(e)}


def unsave_user_item(user_id: int, item_id: str) -> dict:
    """
    Unsave an item for a user on Reddit and remove from local database.

    Args:
        user_id: The user's database ID
        item_id: The reddit_id of the item to unsave

    Returns:
        Dict with status
    """
    from flask import current_app

    user = User.query.get(user_id)

    if not user:
        return {"error": "User not found"}

    # Find the item
    item = SavedItem.query.filter_by(user_id=user_id, reddit_id=item_id).first()
    if not item:
        return {"error": "Item not found"}

    try:
        # Check if token needs refresh
        if user.is_token_expired():
            from .auth import refresh_access_token
            if not refresh_access_token(user):
                return {"error": "Token refresh failed"}

        # Unsave on Reddit
        sync_service = RedditSyncService(user, current_app.config)
        sync_service.unsave_item(item.reddit_fullname)

        # Remove from local database
        db.session.delete(item)
        db.session.commit()

        return {"status": "success"}

    except RedditAPIError as e:
        return {"error": str(e)}

    except Exception as e:
        current_app.logger.error(f"Unsave error for user {user_id}, item {item_id}: {e}")
        return {"error": str(e)}
