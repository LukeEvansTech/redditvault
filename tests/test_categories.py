"""Tests for category mapping."""

from webapp.categories import categorize_subreddit, get_all_categories, CATEGORIES


def test_categorize_known_subreddit():
    assert categorize_subreddit("homelab") == "Self-Hosting & Homelab"
    assert categorize_subreddit("ClaudeAI") == "AI & LLMs"
    assert categorize_subreddit("LiverpoolFC") == "Sports"


def test_categorize_unknown_subreddit():
    assert categorize_subreddit("unknownsubreddit") == "Uncategorized"


def test_get_all_categories():
    cats = get_all_categories()
    assert "Self-Hosting & Homelab" in cats
    assert "Uncategorized" in cats
    assert len(cats) == len(CATEGORIES) + 1


def test_categories_no_duplicate_subreddits():
    seen = {}
    for category, subs in CATEGORIES.items():
        for sub in subs:
            assert sub not in seen, f"{sub} is in both '{seen[sub]}' and '{category}'"
            seen[sub] = category
