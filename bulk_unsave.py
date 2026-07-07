#!/usr/bin/env python3
"""
Bulk unsave Reddit items.

Usage:
    python bulk_unsave.py [--dry-run] [--file FILE]

This script reads URLs from duplicates_to_unsave.md (or specified file)
and unsaves them from Reddit using the existing webapp infrastructure.
"""

import os
import sys
import re
import time
import argparse


def extract_urls_from_markdown(filepath: str) -> list[str]:
    """Extract Reddit URLs from the markdown file."""
    urls = []
    in_code_block = False

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()

            # Track code blocks
            if line.startswith('```'):
                in_code_block = not in_code_block
                continue

            # Only extract URLs from code blocks (the quick unsave list)
            if in_code_block and line.startswith('https://reddit.com/'):
                urls.append(line)

    return urls


def normalize_permalink(url: str) -> str:
    """Convert URL to the permalink format stored in database."""
    # URLs in file: https://reddit.com/r/...
    # Database format: https://reddit.com/r/...
    # They should match, but let's normalize just in case
    url = url.rstrip('/')
    return url


def main():
    parser = argparse.ArgumentParser(description='Bulk unsave Reddit items')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be unsaved without actually doing it')
    parser.add_argument('--file', default='duplicates_to_unsave.md',
                        help='Markdown file with URLs to unsave')
    parser.add_argument('--user', help='Reddit username (if multiple users in DB)')
    args = parser.parse_args()

    # Get the file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, args.file)

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    # Extract URLs
    urls = extract_urls_from_markdown(filepath)
    print(f"Found {len(urls)} URLs to unsave")

    if not urls:
        print("No URLs found in the quick unsave list section")
        sys.exit(1)

    if args.dry_run:
        print("\n=== DRY RUN - No changes will be made ===\n")
        for url in urls:
            print(f"  Would unsave: {url}")
        print(f"\nTotal: {len(urls)} items")
        sys.exit(0)

    # Set up Flask app context
    sys.path.insert(0, script_dir)
    os.chdir(script_dir)

    from webapp import create_app
    from webapp.extensions import db
    from webapp.models import User, SavedItem
    from webapp.sync import RedditSyncService
    from webapp.auth import refresh_access_token

    app = create_app()

    with app.app_context():
        # Get the user
        if args.user:
            user = User.query.filter_by(username=args.user).first()
        else:
            user = User.query.first()

        if not user:
            print("Error: No user found in database. Please log in via the webapp first.")
            sys.exit(1)

        print(f"Using user: {user.username}")

        # Check/refresh token
        if user.is_token_expired():
            print("Token expired, refreshing...")
            if not refresh_access_token(user):
                print("Error: Could not refresh token. Please log in again via the webapp.")
                sys.exit(1)
            print("Token refreshed successfully")

        # Create sync service
        sync_service = RedditSyncService(user, app.config)

        # Process each URL
        success_count = 0
        not_found_count = 0
        error_count = 0

        for i, url in enumerate(urls, 1):
            permalink = normalize_permalink(url)

            # Find item in database
            item = SavedItem.query.filter_by(user_id=user.id).filter(
                SavedItem.permalink.like(f"%{permalink.split('reddit.com')[-1]}%")
            ).first()

            if not item:
                print(f"[{i}/{len(urls)}] NOT FOUND in DB: {url}")
                not_found_count += 1
                continue

            try:
                # Unsave on Reddit
                sync_service.unsave_item(item.reddit_fullname)

                # Remove from local database
                db.session.delete(item)
                db.session.commit()

                print(f"[{i}/{len(urls)}] UNSAVED: {item.title or item.post_title or url}")
                success_count += 1

                # Rate limiting - be gentle with Reddit API
                time.sleep(0.5)

            except Exception as e:
                print(f"[{i}/{len(urls)}] ERROR: {url} - {e}")
                error_count += 1

        # Summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print(f"Successfully unsaved: {success_count}")
        print(f"Not found in DB:      {not_found_count}")
        print(f"Errors:               {error_count}")
        print(f"Total processed:      {len(urls)}")


if __name__ == "__main__":
    main()
