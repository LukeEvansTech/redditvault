#!/usr/bin/env python3
"""
Bulk unsave Reddit items using script app + 1Password credentials.

Usage:
    python bulk_unsave_script.py [--dry-run]
"""

import os
import sys
import json
import time
import subprocess
import requests

# 1Password items
OP_USER_ITEM = "reddit.com - LukeEvansTech"
OP_APP_ITEM = "PowerShell Reddit App (Script)"
USER_AGENT = "BulkUnsave/1.0 by SolidCactus"


def get_credentials():
    """Fetch all credentials from 1Password."""
    try:
        # User credentials
        username = subprocess.run(
            ['op', 'item', 'get', OP_USER_ITEM, '--fields', 'username'],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        password = subprocess.run(
            ['op', 'item', 'get', OP_USER_ITEM, '--fields', 'password'],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        totp = subprocess.run(
            ['op', 'item', 'get', OP_USER_ITEM, '--otp'],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        # Script app credentials
        client_id = subprocess.run(
            ['op', 'item', 'get', OP_APP_ITEM, '--fields', 'Client ID'],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        client_secret = subprocess.run(
            ['op', 'item', 'get', OP_APP_ITEM, '--fields', 'Client Secret'],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        return username, password, totp, client_id, client_secret

    except subprocess.CalledProcessError as e:
        print(f"Error getting credentials from 1Password: {e}")
        print("Make sure you're signed in: op signin")
        sys.exit(1)


def get_access_token(username: str, password: str, totp: str, client_id: str, client_secret: str) -> str:
    """Get Reddit access token using password grant with 2FA."""

    # For script apps, append 2FA code to password
    password_with_2fa = f"{password}:{totp}"

    response = requests.post(
        'https://www.reddit.com/api/v1/access_token',
        auth=(client_id, client_secret),
        data={
            'grant_type': 'password',
            'username': username,
            'password': password_with_2fa,
        },
        headers={'User-Agent': USER_AGENT}
    )

    if response.status_code != 200:
        print(f"Error getting access token: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)

    data = response.json()

    if 'error' in data:
        print(f"Auth error: {data.get('error')} - {data.get('message', '')}")
        sys.exit(1)

    return data['access_token']


def unsave_item(access_token: str, fullname: str) -> bool:
    """Unsave an item on Reddit."""
    response = requests.post(
        'https://oauth.reddit.com/api/unsave',
        headers={
            'Authorization': f'Bearer {access_token}',
            'User-Agent': USER_AGENT
        },
        data={'id': fullname}
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
    username, password, totp, client_id, client_secret = get_credentials()
    print(f"Got credentials for user: {username}")
    print(f"Using script app: {client_id[:8]}...")

    # Authenticate with Reddit
    print("Authenticating with Reddit...")
    access_token = get_access_token(username, password, totp, client_id, client_secret)
    print("Authenticated successfully!\n")

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
            if unsave_item(access_token, fullname):
                title = item.get('title') or item.get('body', '')[:50] or url
                print(f"[{i}/{len(urls)}] UNSAVED: {title[:60]}")
                success += 1
            else:
                print(f"[{i}/{len(urls)}] FAILED: {url}")
                errors += 1

            # Rate limit
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


if __name__ == "__main__":
    main()
