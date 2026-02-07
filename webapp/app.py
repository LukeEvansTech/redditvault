#!/usr/bin/env python3
"""Web UI for browsing Reddit saved items."""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, g
from flask_login import login_required, current_user
from sqlalchemy import func
from .config import Config
from .extensions import db, login_manager
from .models import User, SavedItem, ApiKey
from .auth import auth_bp
from .api_auth import api_auth_required, generate_api_key


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp)

    # Create database tables (handled gracefully for multi-worker setup)
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            # Tables may already exist if another worker created them
            pass

    # Routes
    @app.route("/")
    def index():
        """Home page with category overview."""
        if not current_user.is_authenticated:
            return render_template("login.html")

        # Get categories with counts
        category_stats = db.session.query(
            SavedItem.category,
            func.count(SavedItem.id).label("count"),
            func.sum(SavedItem.reviewed.cast(db.Integer)).label("reviewed")
        ).filter_by(user_id=current_user.id).group_by(SavedItem.category).all()

        categories = []
        for cat, count, reviewed in category_stats:
            categories.append({
                "name": cat or "Uncategorized",
                "count": count,
                "reviewed": reviewed or 0,
            })

        categories.sort(key=lambda x: -x["count"])

        total = sum(c["count"] for c in categories)
        total_reviewed = sum(c["reviewed"] for c in categories)

        return render_template(
            "index.html",
            categories=categories,
            total=total,
            total_reviewed=total_reviewed,
        )

    @app.route("/category/<name>")
    @login_required
    def category(name):
        """View items in a category."""
        filter_type = request.args.get("type", "all")
        filter_status = request.args.get("status", "all")
        search = request.args.get("q", "").lower()

        # Base query
        query = SavedItem.query.filter_by(user_id=current_user.id, category=name)

        # Apply type filter
        if filter_type != "all":
            query = query.filter_by(item_type=filter_type)

        # Apply status filter
        if filter_status == "reviewed":
            query = query.filter_by(reviewed=True)
        elif filter_status == "unreviewed":
            query = query.filter_by(reviewed=False)

        # Apply search
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    SavedItem.title.ilike(search_pattern),
                    SavedItem.body.ilike(search_pattern),
                    SavedItem.selftext.ilike(search_pattern),
                    SavedItem.subreddit.ilike(search_pattern),
                )
            )

        # Get total count before limiting
        total = SavedItem.query.filter_by(user_id=current_user.id, category=name).count()

        # Get filtered items
        items = query.order_by(SavedItem.created_utc.desc()).all()

        # Get subreddits in this category
        subreddits = db.session.query(SavedItem.subreddit).filter_by(
            user_id=current_user.id, category=name
        ).distinct().all()
        subreddits = sorted([s[0] for s in subreddits])

        return render_template(
            "category.html",
            name=name,
            items=items,
            total=total,
            subreddits=subreddits,
            filter_type=filter_type,
            filter_status=filter_status,
            search=search,
        )

    @app.route("/search")
    @login_required
    def search():
        """Search across all items."""
        query_str = request.args.get("q", "").lower()

        if not query_str:
            return render_template("search.html", items=[], query="", total=0)

        search_pattern = f"%{query_str}%"
        query = SavedItem.query.filter_by(user_id=current_user.id).filter(
            db.or_(
                SavedItem.title.ilike(search_pattern),
                SavedItem.body.ilike(search_pattern),
                SavedItem.selftext.ilike(search_pattern),
                SavedItem.subreddit.ilike(search_pattern),
            )
        )

        total = query.count()
        items = query.order_by(SavedItem.created_utc.desc()).limit(100).all()

        return render_template("search.html", items=items, query=query_str, total=total)

    # --- API endpoints (session + API key auth) ---

    @app.route("/api/item/<item_id>/state", methods=["POST"])
    @api_auth_required
    def update_item_state(item_id):
        """Update item state (reviewed, notes, etc.)."""
        item = SavedItem.query.filter_by(
            user_id=g.api_user.id, reddit_id=item_id
        ).first_or_404()

        data = request.json
        if "reviewed" in data:
            item.reviewed = data["reviewed"]
        if "notes" in data:
            item.notes = data["notes"]
        if "archived" in data:
            item.archived = data["archived"]

        db.session.commit()

        return jsonify({
            "success": True,
            "state": {
                "reviewed": item.reviewed,
                "archived": item.archived,
                "notes": item.notes,
            }
        })

    @app.route("/api/stats")
    @api_auth_required
    def stats():
        """Get statistics."""
        total = SavedItem.query.filter_by(user_id=g.api_user.id).count()
        reviewed = SavedItem.query.filter_by(user_id=g.api_user.id, reviewed=True).count()

        by_type = {}
        type_counts = db.session.query(
            SavedItem.item_type, func.count(SavedItem.id)
        ).filter_by(user_id=g.api_user.id).group_by(SavedItem.item_type).all()

        for item_type, count in type_counts:
            by_type[item_type] = count

        categories = db.session.query(SavedItem.category).filter_by(
            user_id=g.api_user.id
        ).distinct().count()

        return jsonify({
            "total": total,
            "reviewed": reviewed,
            "by_type": by_type,
            "categories": categories,
            "last_sync": g.api_user.last_sync_at.isoformat() if g.api_user.last_sync_at else None,
            "sync_in_progress": g.api_user.sync_in_progress,
        })

    @app.route("/api/sync", methods=["POST"])
    @api_auth_required
    def trigger_sync():
        """Trigger a sync of saved items."""
        if g.api_user.sync_in_progress:
            return jsonify({"error": "Sync already in progress"}), 409

        full_sync = request.json.get("full", False) if request.json else False

        from .sync import sync_user_items
        result = sync_user_items(g.api_user.id, full_sync)

        return jsonify(result)

    @app.route("/api/item/<item_id>/unsave", methods=["POST"])
    @api_auth_required
    def unsave_item(item_id):
        """Unsave an item from Reddit and remove from local database."""
        from .sync import unsave_user_item
        result = unsave_user_item(g.api_user.id, item_id)

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result)

    @app.route("/api/sync/status")
    @api_auth_required
    def sync_status():
        """Get current sync status."""
        return jsonify({
            "sync_in_progress": g.api_user.sync_in_progress,
            "last_sync": g.api_user.last_sync_at.isoformat() if g.api_user.last_sync_at else None,
        })

    # --- API key management (browser session only) ---

    @app.route("/settings/api-keys")
    @login_required
    def api_keys_page():
        """API keys management page."""
        keys = ApiKey.query.filter_by(user_id=current_user.id).order_by(ApiKey.created_at.desc()).all()
        return render_template("api_keys.html", keys=keys)

    @app.route("/api/keys", methods=["POST"])
    @login_required
    def create_api_key():
        """Create a new API key."""
        data = request.json or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Key name is required"}), 400

        raw_key, key_hash = generate_api_key()

        api_key = ApiKey(
            user_id=current_user.id,
            key_hash=key_hash,
            name=name,
        )
        db.session.add(api_key)
        db.session.commit()

        return jsonify({
            "id": api_key.id,
            "name": api_key.name,
            "key": raw_key,
            "created_at": api_key.created_at.isoformat(),
        })

    @app.route("/api/keys", methods=["GET"])
    @login_required
    def list_api_keys():
        """List user's API keys (masked)."""
        keys = ApiKey.query.filter_by(user_id=current_user.id).order_by(ApiKey.created_at.desc()).all()
        return jsonify([{
            "id": k.id,
            "name": k.name,
            "created_at": k.created_at.isoformat(),
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "is_active": k.is_active,
        } for k in keys])

    @app.route("/api/keys/<int:key_id>", methods=["DELETE"])
    @login_required
    def revoke_api_key(key_id):
        """Revoke an API key."""
        api_key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id).first_or_404()
        api_key.is_active = False
        db.session.commit()
        return jsonify({"success": True})

    return app


# For gunicorn: create_app() returns the app
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
