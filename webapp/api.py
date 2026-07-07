"""API routes for programmatic access to saved items."""

from flask import Blueprint, g, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from .extensions import db
from .models import SavedItem, ApiKey
from .api_auth import api_auth_required, generate_api_key

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/item/<item_id>/state", methods=["POST"])
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


@api_bp.route("/api/stats")
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


@api_bp.route("/api/sync", methods=["POST"])
@api_auth_required
def trigger_sync():
    """Trigger a sync of saved items."""
    if g.api_user.sync_in_progress:
        return jsonify({"error": "Sync already in progress"}), 409

    full_sync = request.json.get("full", False) if request.json else False

    from .sync import sync_user_items
    result = sync_user_items(g.api_user.id, full_sync)

    return jsonify(result)


@api_bp.route("/api/item/<item_id>/unsave", methods=["POST"])
@api_auth_required
def unsave_item(item_id):
    """Unsave an item from Reddit and remove from local database."""
    from .sync import unsave_user_item
    result = unsave_user_item(g.api_user.id, item_id)

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)


@api_bp.route("/api/sync/status")
@api_auth_required
def sync_status():
    """Get current sync status."""
    return jsonify({
        "sync_in_progress": g.api_user.sync_in_progress,
        "last_sync": g.api_user.last_sync_at.isoformat() if g.api_user.last_sync_at else None,
    })


@api_bp.route("/settings/api-keys")
@login_required
def api_keys_page():
    """API keys management page."""
    from flask import render_template
    keys = ApiKey.query.filter_by(user_id=current_user.id).order_by(ApiKey.created_at.desc()).all()
    return render_template("api_keys.html", keys=keys)


@api_bp.route("/api/keys", methods=["POST"])
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


@api_bp.route("/api/keys", methods=["GET"])
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


@api_bp.route("/api/keys/<int:key_id>", methods=["DELETE"])
@login_required
def revoke_api_key(key_id):
    """Revoke an API key."""
    api_key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id).first_or_404()
    api_key.is_active = False
    db.session.commit()
    return jsonify({"success": True})
