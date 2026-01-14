"""SQLAlchemy database models."""

from datetime import datetime
from flask_login import UserMixin
from .extensions import db


class User(db.Model, UserMixin):
    """Reddit user who authenticated via OAuth."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    reddit_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    username = db.Column(db.String(50), nullable=False)

    # OAuth tokens
    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)

    # Sync tracking
    last_sync_at = db.Column(db.DateTime, nullable=True)
    sync_in_progress = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    saved_items = db.relationship(
        "SavedItem", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def is_token_expired(self):
        """Check if access token needs refresh."""
        if not self.token_expires_at:
            return True
        # Refresh 5 minutes early to avoid edge cases
        from datetime import timedelta
        return datetime.utcnow() >= (self.token_expires_at - timedelta(minutes=5))


class SavedItem(db.Model):
    """A saved post or comment from Reddit."""

    __tablename__ = "saved_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Reddit identifiers
    reddit_id = db.Column(db.String(20), nullable=False)
    reddit_fullname = db.Column(db.String(20), nullable=False)

    # Content type
    item_type = db.Column(db.String(10), nullable=False)  # 'post' or 'comment'

    # Common fields
    subreddit = db.Column(db.String(50), nullable=False, index=True)
    author = db.Column(db.String(50), nullable=True)
    permalink = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, default=0)
    created_utc = db.Column(db.DateTime, nullable=False, index=True)

    # Post-specific fields
    title = db.Column(db.Text, nullable=True)
    url = db.Column(db.Text, nullable=True)
    selftext = db.Column(db.Text, nullable=True)
    is_self = db.Column(db.Boolean, nullable=True)
    num_comments = db.Column(db.Integer, nullable=True)

    # Comment-specific fields
    body = db.Column(db.Text, nullable=True)
    post_title = db.Column(db.Text, nullable=True)

    # Categorization
    category = db.Column(db.String(100), nullable=True, index=True)

    # Sync tracking
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

    # User state (embedded for simplicity)
    reviewed = db.Column(db.Boolean, default=False)
    archived = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "reddit_id", name="uq_user_reddit_item"),
        db.Index("ix_saved_items_user_category", "user_id", "category"),
    )
