#!/usr/bin/env python3
"""
Bulk unsave Reddit items using OAuth.
Opens browser once to authorize, then processes all items.

Usage:
    python bulk_unsave_oauth.py [--dry-run]
"""

import os
import sys
import json
import time
import webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, parse_qs, urlparse
import threading

# Load .env
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:8765/callback'
USER_AGENT = 'BulkUnsave/1.0'

auth_code = None
server_done = threading.Event()


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)

        if parsed.path == '/callback':
            params = parse_qs(parsed.query)
            if 'code' in params:
                auth_code = params['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''<html><body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #1a1a1a; color: #fff;">
                    <div style="text-align: center;">
                        <h1 style="color: #4ade80;">Authorization Successful!</h1>
                        <p>You can close this window and return to the terminal.</p>
                    </div>
                </body></html>''')
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Authorization failed</h1></body></html>')
            server_done.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def get_access_token():
    """Get access token via OAuth flow."""
    global auth_code

    # Check for cached token
    token_file = os.path.join(os.path.dirname(__file__), '.reddit_token')
    if os.path.exists(token_file):
        with open(token_file) as f:
            data = json.load(f)
            if data.get('expires_at', 0) > time.time() + 300:
                return data['access_token']
            if data.get('refresh_token'):
                new_token = refresh_token(data['refresh_token'])
                if new_token:
                    return new_token

    print("\n" + "="*50)
    print("REDDIT AUTHORIZATION REQUIRED")
    print("="*50)
    print("\nOpening browser for Reddit authorization...")
    print("Please log in and authorize the app.\n")

    state = 'bulk_unsave_' + str(int(time.time()))
    auth_params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'state': state,
        'redirect_uri': REDIRECT_URI,
        'duration': 'permanent',
        'scope': 'identity history save'
    }
    auth_url = f"https://www.reddit.com/api/v1/authorize?{urlencode(auth_params)}"

    server = HTTPServer(('localhost', 8765), OAuthHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()

    webbrowser.open(auth_url)

    print("Waiting for authorization... (timeout: 2 minutes)")
    server_done.wait(timeout=120)
    server.server_close()

    if not auth_code:
        print("Error: Authorization timed out or failed")
        sys.exit(1)

    print("Authorization received! Getting access token...")

    response = requests.post(
        'https://www.reddit.com/api/v1/access_token',
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': REDIRECT_URI
        },
        headers={'User-Agent': USER_AGENT}
    )

    if response.status_code != 200:
        print(f"Error getting token: {response.status_code} {response.text}")
        sys.exit(1)

    token_info = response.json()

    if 'error' in token_info:
        print(f"Auth error: {token_info}")
        sys.exit(1)

    save_data = {
        'access_token': token_info['access_token'],
        'refresh_token': token_info.get('refresh_token'),
        'expires_at': time.time() + token_info.get('expires_in', 3600)
    }
    with open(token_file, 'w') as f:
        json.dump(save_data, f)

    return token_info['access_token']


def refresh_token(refresh_tok):
    """Refresh an expired access token."""
    response = requests.post(
        'https://www.reddit.com/api/v1/access_token',
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_tok
        },
        headers={'User-Agent': USER_AGENT}
    )

    if response.status_code != 200:
        return None

    token_info = response.json()

    token_file = os.path.join(os.path.dirname(__file__), '.reddit_token')
    save_data = {
        'access_token': token_info['access_token'],
        'refresh_token': token_info.get('refresh_token', refresh_tok),
        'expires_at': time.time() + token_info.get('expires_in', 3600)
    }
    with open(token_file, 'w') as f:
        json.dump(save_data, f)

    return token_info['access_token']


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

    # Get access token (opens browser if needed)
    access_token = get_access_token()
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
