"""Reddit OAuth2 authentication routes."""

import secrets
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta
from flask import Blueprint, redirect, request, session, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from .extensions import db
from .models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login")
def login():
    """Initiate Reddit OAuth flow."""
    if current_user.is_authenticated:
        return redirect("/")

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "client_id": current_app.config["REDDIT_CLIENT_ID"],
        "response_type": "code",
        "state": state,
        "redirect_uri": current_app.config["REDDIT_REDIRECT_URI"],
        "duration": "permanent",  # Get refresh token
        "scope": " ".join(current_app.config["REDDIT_SCOPES"]),
    }

    auth_url = f"https://www.reddit.com/api/v1/authorize?{urlencode(params)}"
    return redirect(auth_url)


@auth_bp.route("/callback")
def callback():
    """Handle Reddit OAuth callback."""
    # Verify state
    state = request.args.get("state")
    stored_state = session.pop("oauth_state", None)

    if state != stored_state:
        flash("Invalid state parameter. Please try again.", "error")
        return redirect("/")

    # Check for errors
    error = request.args.get("error")
    if error:
        flash(f"Reddit authorization failed: {error}", "error")
        return redirect("/")

    # Exchange code for tokens
    code = request.args.get("code")
    tokens = exchange_code_for_tokens(code)

    if not tokens:
        flash("Failed to get access token. Please try again.", "error")
        return redirect("/")

    # Get user identity from Reddit
    user_info = get_reddit_user_info(tokens["access_token"])

    if not user_info:
        flash("Failed to get user info from Reddit.", "error")
        return redirect("/")

    # Find or create user
    user = User.query.filter_by(reddit_id=user_info["id"]).first()
    is_new_user = user is None

    if not user:
        user = User(
            reddit_id=user_info["id"],
            username=user_info["name"],
        )
        db.session.add(user)

    # Update tokens
    user.access_token = tokens["access_token"]
    user.refresh_token = tokens.get("refresh_token", user.refresh_token)
    user.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
    user.updated_at = datetime.utcnow()

    db.session.commit()

    # Log in user
    login_user(user, remember=True)

    if is_new_user:
        flash(f"Welcome, u/{user.username}! Starting to sync your saved items...", "success")
    else:
        flash(f"Welcome back, u/{user.username}!", "success")

    return redirect("/")


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out user."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect("/")


def exchange_code_for_tokens(code: str) -> dict | None:
    """Exchange authorization code for access and refresh tokens."""
    auth = (
        current_app.config["REDDIT_CLIENT_ID"],
        current_app.config["REDDIT_CLIENT_SECRET"],
    )

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": current_app.config["REDDIT_REDIRECT_URI"],
    }

    headers = {
        "User-Agent": current_app.config["REDDIT_USER_AGENT"],
    }

    try:
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()

        current_app.logger.error(f"Token exchange failed: {response.status_code} {response.text}")
    except requests.RequestException as e:
        current_app.logger.error(f"Token exchange error: {e}")

    return None


def get_reddit_user_info(access_token: str) -> dict | None:
    """Get user identity from Reddit API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": current_app.config["REDDIT_USER_AGENT"],
    }

    try:
        response = requests.get(
            "https://oauth.reddit.com/api/v1/me",
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()

        current_app.logger.error(f"User info failed: {response.status_code} {response.text}")
    except requests.RequestException as e:
        current_app.logger.error(f"User info error: {e}")

    return None


def refresh_access_token(user: User) -> bool:
    """Refresh expired access token using refresh token."""
    if not user.refresh_token:
        return False

    auth = (
        current_app.config["REDDIT_CLIENT_ID"],
        current_app.config["REDDIT_CLIENT_SECRET"],
    )

    data = {
        "grant_type": "refresh_token",
        "refresh_token": user.refresh_token,
    }

    headers = {
        "User-Agent": current_app.config["REDDIT_USER_AGENT"],
    }

    try:
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            tokens = response.json()
            user.access_token = tokens["access_token"]
            user.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
            if "refresh_token" in tokens:
                user.refresh_token = tokens["refresh_token"]
            db.session.commit()
            return True

        current_app.logger.error(f"Token refresh failed: {response.status_code} {response.text}")
    except requests.RequestException as e:
        current_app.logger.error(f"Token refresh error: {e}")

    return False
