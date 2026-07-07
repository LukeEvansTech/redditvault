"""Web view routes for browsing Reddit saved items."""

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func
from .extensions import db
from .models import SavedItem

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Home page with paginated recent items and subreddit nav."""
    if not current_user.is_authenticated:
        return render_template("login.html")

    PER_PAGE = 20

    page = request.args.get("page", 1, type=int)
    current_subreddit = request.args.get("subreddit", None)

    subreddit_stats = db.session.query(
        SavedItem.subreddit,
        func.count(SavedItem.id).label("count")
    ).filter_by(user_id=current_user.id).group_by(
        SavedItem.subreddit
    ).order_by(func.count(SavedItem.id).desc()).all()

    subreddits = [{"name": name, "count": count} for name, count in subreddit_stats]

    query = SavedItem.query.filter_by(user_id=current_user.id)
    if current_subreddit:
        query = query.filter_by(subreddit=current_subreddit)

    total = query.count()
    pagination = query.order_by(SavedItem.created_utc.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )

    return render_template(
        "index.html",
        items=pagination.items,
        pagination=pagination,
        subreddits=subreddits,
        current_subreddit=current_subreddit,
        total=total,
    )


@views_bp.route("/category/<name>")
@login_required
def category(name):
    """View items in a category."""
    filter_type = request.args.get("type", "all")
    filter_status = request.args.get("status", "all")
    search = request.args.get("q", "").lower()

    query = SavedItem.query.filter_by(user_id=current_user.id, category=name)

    if filter_type != "all":
        query = query.filter_by(item_type=filter_type)

    if filter_status == "reviewed":
        query = query.filter_by(reviewed=True)
    elif filter_status == "unreviewed":
        query = query.filter_by(reviewed=False)

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

    total = SavedItem.query.filter_by(user_id=current_user.id, category=name).count()
    items = query.order_by(SavedItem.created_utc.desc()).all()

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


@views_bp.route("/search")
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
