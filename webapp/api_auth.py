"""API key authentication for programmatic access."""

import hashlib
import secrets
from datetime import datetime
from functools import wraps

from flask import g, jsonify, request
from flask_login import current_user

from .extensions import db
from .models import ApiKey, User


def generate_api_key():
    """Generate a new API key.

    Returns:
        Tuple of (raw_key, key_hash). Raw key is shown once at creation.
    """
    raw_key = secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def verify_api_key(raw_key):
    """Verify an API key and return the associated user.

    Returns:
        User instance if valid, None otherwise.
    """
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = ApiKey.query.filter_by(key_hash=key_hash, is_active=True).first()

    if not api_key:
        return None

    api_key.last_used_at = datetime.utcnow()
    db.session.commit()

    return api_key.user


def api_auth_required(f):
    """Decorator that accepts both session auth and API key auth.

    Checks Flask-Login session first (browser), then falls back to
    API key from Authorization header or X-API-Key header.
    Sets g.api_user to the authenticated user.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Try session auth first (browser)
        if current_user.is_authenticated:
            g.api_user = current_user
            return f(*args, **kwargs)

        # Try API key from headers
        api_key = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]

        if not api_key:
            api_key = request.headers.get("X-API-Key")

        if not api_key:
            return jsonify({"error": "Authentication required"}), 401

        user = verify_api_key(api_key)
        if not user:
            return jsonify({"error": "Invalid API key"}), 401

        g.api_user = user
        return f(*args, **kwargs)

    return decorated
