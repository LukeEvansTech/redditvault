#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "praw>=7.7.0",
# ]
# ///
"""Export Reddit saved items to JSON for organization."""

import json
import os
import subprocess
import sys
from datetime import datetime

import praw


def log(msg: str):
    """Print with immediate flush."""
    print(msg, flush=True)


def get_op_field(item: str, field: str, vault: str = "Home Operations") -> str:
    """Get a field from 1Password."""
    result = subprocess.run(
        ["op", "item", "get", item, "--vault", vault, "--fields", f"label={field}", "--reveal"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return result.stdout.strip()


def get_op_totp(item: str, vault: str) -> str:
    """Get TOTP code from 1Password."""
    result = subprocess.run(
        ["op", "item", "get", item, "--vault", vault, "--otp"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return result.stdout.strip()


def get_reddit_client():
    """Create authenticated Reddit client using 1Password credentials."""
    log("Fetching credentials from 1Password...")

    # Get 1Password item name from environment or use default
    op_reddit_item = os.environ.get("OP_REDDIT_ITEM", "reddit.com")
    op_reddit_vault = os.environ.get("OP_REDDIT_VAULT", "Personal")

    # Get login credentials and TOTP from Personal vault
    username = get_op_field(op_reddit_item, "username", op_reddit_vault)
    password = get_op_field(op_reddit_item, "password", op_reddit_vault)
    totp_code = get_op_totp(op_reddit_item, op_reddit_vault)

    # Get API credentials from Home Operations vault
    client_id = get_op_field("Reddit API", "client_id")
    client_secret = get_op_field("Reddit API", "client_secret")

    password_with_2fa = f"{password}:{totp_code}"

    log(f"  Username: {username}")
    log(f"  Client ID: {client_id[:8]}...")
    log(f"  TOTP: {totp_code}")
    log(f"  Password length: {len(password)}, with 2FA: {len(password_with_2fa)}")

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password_with_2fa,
        user_agent="SavedItemsExporter/1.0",
    )


def export_saved_items(reddit, limit=None):
    """Fetch all saved items and return as structured data."""
    saved_items = []

    log("Fetching saved items...")
    for item in reddit.user.me().saved(limit=limit):
        if isinstance(item, praw.models.Submission):
            saved_items.append({
                "type": "post",
                "id": item.id,
                "title": item.title,
                "subreddit": item.subreddit.display_name,
                "url": item.url,
                "permalink": f"https://reddit.com{item.permalink}",
                "author": str(item.author) if item.author else "[deleted]",
                "score": item.score,
                "created_utc": datetime.utcfromtimestamp(item.created_utc).isoformat(),
                "selftext": item.selftext[:500] if item.selftext else None,
                "is_self": item.is_self,
                "num_comments": item.num_comments,
            })
        elif isinstance(item, praw.models.Comment):
            saved_items.append({
                "type": "comment",
                "id": item.id,
                "body": item.body[:500] if item.body else None,
                "subreddit": item.subreddit.display_name,
                "permalink": f"https://reddit.com{item.permalink}",
                "author": str(item.author) if item.author else "[deleted]",
                "score": item.score,
                "created_utc": datetime.utcfromtimestamp(item.created_utc).isoformat(),
                "post_title": item.submission.title,
            })

        if len(saved_items) % 25 == 0:
            log(f"  Fetched {len(saved_items)} items...")

    return saved_items


def main():
    reddit = get_reddit_client()

    # Verify authentication
    log(f"Authenticated as: {reddit.user.me().name}")

    # Export all saved items
    saved_items = export_saved_items(reddit)

    # Save to JSON
    output_file = "saved_items.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(saved_items, f, indent=2, ensure_ascii=False)

    log(f"\nExported {len(saved_items)} items to {output_file}")

    # Print summary by subreddit
    subreddits = {}
    for item in saved_items:
        sub = item["subreddit"]
        subreddits[sub] = subreddits.get(sub, 0) + 1

    log("\nTop subreddits:")
    for sub, count in sorted(subreddits.items(), key=lambda x: -x[1])[:15]:
        log(f"  r/{sub}: {count}")


if __name__ == "__main__":
    main()
