#!/usr/bin/env python3
"""
Bulk unsave Reddit items using 1Password for authentication.
Uses session-based login (like a browser) since the Reddit app is web-type.

Usage:
    python bulk_unsave_1password.py [--dry-run]
"""

import os
import sys
import json
import time
import subprocess
import requests

# Config
OP_ITEM = "reddit.com - SolidCactus"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def get_credentials_from_1password():
    """Fetch Reddit credentials from 1Password."""
    try:
        username = subprocess.run(
            ['op', 'item', 'get', OP_ITEM, '--fields', 'username'],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        password = subprocess.run(
            ['op', 'item', 'get', OP_ITEM, '--fields', 'password'],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        totp = subprocess.run(
            ['op', 'item', 'get', OP_ITEM, '--otp'],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        return username, password, totp

    except subprocess.CalledProcessError as e:
        print(f"Error getting credentials from 1Password: {e}")
        print("Make sure you're signed in: op signin")
        sys.exit(1)


class RedditSession:
    """Handle Reddit authentication and API calls via session."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.modhash = None

    def login(self, username: str, password: str, totp: str) -> bool:
        """Login to Reddit with username, password, and 2FA."""

        # Get the login page to get csrf token
        login_page = self.session.get('https://www.reddit.com/login')

        # Login request
        login_data = {
            'username': username,
            'password': password,
            'otp': totp,
        }

        # Use the API endpoint
        response = self.session.post(
            'https://www.reddit.com/api/login',
            data={
                'user': username,
                'passwd': password,
                'otp': totp,
                'api_type': 'json',
            },
            headers={'User-Agent': USER_AGENT}
        )

        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")
            return False

        data = response.json()

        if 'json' in data and 'data' in data['json']:
            json_data = data['json']['data']
            if 'modhash' in json_data:
                self.modhash = json_data['modhash']
                # Also set cookie if provided
                if 'cookie' in json_data:
                    self.session.cookies.set('reddit_session', json_data['cookie'])
                return True

        if 'json' in data and 'errors' in data['json']:
            errors = data['json']['errors']
            if errors:
                print(f"Login errors: {errors}")
                return False

        # Check if we're actually logged in by visiting a page
        me_response = self.session.get('https://www.reddit.com/api/me.json')
        if me_response.status_code == 200:
            me_data = me_response.json()
            if me_data.get('data', {}).get('name'):
                return True

        return False

    def unsave(self, fullname: str) -> bool:
        """Unsave an item."""
        response = self.session.post(
            'https://www.reddit.com/api/unsave',
            data={
                'id': fullname,
                'uh': self.modhash or '',
            }
        )
        return response.status_code in (200, 202)


def extract_urls_from_markdown(filepath: str) -> list[str]:
    """Extract Reddit URLs from the markdown file."""
    urls = []
    in_code_block = False

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block and line.startswith('https://reddit.com/'):
                urls.append(line)
    return urls


def load_saved_items(filepath: str) -> dict:
    """Load saved items and index by permalink."""
    with open(filepath) as f:
        items = json.load(f)

    lookup = {}
    for item in items:
        permalink = item.get('permalink', '')
        normalized = permalink.rstrip('/')
        lookup[normalized] = item

    return lookup


def match_url_to_item(url: str, saved_items: dict):
    """Try to match a URL to a saved item."""
    if 'reddit.com' in url:
        path = '/' + url.split('reddit.com/')[-1]
    else:
        path = url

    path = path.rstrip('/')

    if path in saved_items:
        return saved_items[path]

    parts = path.split('/')
    if len(parts) >= 5 and parts[3] == 'comments':
        post_id = parts[4]
        for permalink, item in saved_items.items():
            if f'/comments/{post_id}/' in permalink:
                return item

    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bulk unsave Reddit items')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be unsaved')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))

    md_file = os.path.join(script_dir, 'duplicates_to_unsave.md')
    urls = extract_urls_from_markdown(md_file)
    print(f"Found {len(urls)} URLs to unsave")

    if not urls:
        print("No URLs found")
        sys.exit(1)

    saved_file = os.path.join(script_dir, 'saved_items.json')
    saved_items = load_saved_items(saved_file)
    print(f"Loaded {len(saved_items)} saved items for lookup")

    if args.dry_run:
        print("\n=== DRY RUN ===\n")
        found = 0
        not_found = 0
        for url in urls:
            item = match_url_to_item(url, saved_items)
            if item:
                title = item.get('title', item.get('body', '')[:50])
                print(f"  FOUND: {title[:60]}")
                found += 1
            else:
                print(f"  NOT FOUND: {url}")
                not_found += 1
        print(f"\nFound: {found}, Not found: {not_found}")
        sys.exit(0)

    # Get credentials from 1Password
    print("\nFetching credentials from 1Password...")
    username, password, totp = get_credentials_from_1password()
    print(f"Got credentials for: {username}")

    # Create Reddit session and login
    print("Logging into Reddit...")
    reddit = RedditSession()

    if not reddit.login(username, password, totp):
        print("Login failed. Trying alternative method...")

        # Try using PRAW if available
        try:
            import praw

            # Load env
            load_env_file = os.path.join(script_dir, '.env')
            client_id = None
            client_secret = None

            if os.path.exists(load_env_file):
                with open(load_env_file) as f:
                    for line in f:
                        if line.startswith('REDDIT_CLIENT_ID='):
                            client_id = line.split('=', 1)[1].strip()
                        elif line.startswith('REDDIT_CLIENT_SECRET='):
                            client_secret = line.split('=', 1)[1].strip()

            reddit_praw = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                username=username,
                password=f"{password}:{totp}",
                user_agent=USER_AGENT
            )

            print(f"Logged in as: {reddit_praw.user.me()}")

            # Process with PRAW
            success = 0
            not_found = 0
            errors = 0

            for i, url in enumerate(urls, 1):
                item = match_url_to_item(url, saved_items)

                if not item:
                    print(f"[{i}/{len(urls)}] NOT FOUND: {url}")
                    not_found += 1
                    continue

                item_type = item.get('type', 'post')
                prefix = 't3_' if item_type == 'post' else 't1_'
                fullname = prefix + item['id']

                try:
                    if item_type == 'post':
                        submission = reddit_praw.submission(id=item['id'])
                        submission.unsave()
                    else:
                        comment = reddit_praw.comment(id=item['id'])
                        comment.unsave()

                    title = item.get('title') or item.get('body', '')[:50] or url
                    print(f"[{i}/{len(urls)}] UNSAVED: {title[:60]}")
                    success += 1
                    time.sleep(0.5)

                except Exception as e:
                    print(f"[{i}/{len(urls)}] ERROR: {url} - {e}")
                    errors += 1

            print("\n" + "="*50)
            print("SUMMARY")
            print("="*50)
            print(f"Successfully unsaved: {success}")
            print(f"Not found in JSON:    {not_found}")
            print(f"Errors:               {errors}")
            print(f"Total:                {len(urls)}")
            return

        except ImportError:
            print("\nPRAW not installed. Installing...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'praw'], check=True)
            print("Please run the script again.")
            sys.exit(1)
        except Exception as e:
            print(f"PRAW auth failed: {e}")
            sys.exit(1)

    print("Logged in successfully!\n")

    # Process each URL
    success = 0
    not_found = 0
    errors = 0

    for i, url in enumerate(urls, 1):
        item = match_url_to_item(url, saved_items)

        if not item:
            print(f"[{i}/{len(urls)}] NOT FOUND: {url}")
            not_found += 1
            continue

        item_type = item.get('type', 'post')
        prefix = 't3_' if item_type == 'post' else 't1_'
        fullname = prefix + item['id']

        try:
            if reddit.unsave(fullname):
                title = item.get('title') or item.get('body', '')[:50] or url
                print(f"[{i}/{len(urls)}] UNSAVED: {title[:60]}")
                success += 1
            else:
                print(f"[{i}/{len(urls)}] FAILED: {url}")
                errors += 1

            time.sleep(0.5)

        except Exception as e:
            print(f"[{i}/{len(urls)}] ERROR: {url} - {e}")
            errors += 1

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Successfully unsaved: {success}")
    print(f"Not found in JSON:    {not_found}")
    print(f"Errors:               {errors}")
    print(f"Total:                {len(urls)}")


def load_env():
    pass  # Placeholder for compatibility


if __name__ == "__main__":
    main()
