# RedditVault

Browse and organize your Reddit saved items with a modern glassmorphism UI.

## Features

- **Reddit OAuth Login** - No passwords, just click to authenticate
- **Auto-sync** - Pulls all your saved posts and comments
- **Smart Categories** - Items grouped by topic (Self-Hosting, AI, Gaming, etc.)
- **Track Progress** - Mark items as reviewed
- **Search** - Find anything across all your saves
- **Glassmorphism UI** - Modern frosted glass design

## Quick Start

### Prerequisites

1. Create a Reddit app at https://www.reddit.com/prefs/apps
   - Type: **web app**
   - Redirect URI: `http://localhost:5050/auth/callback`

2. Note your `client_id` and `client_secret`

### Run with Docker

```bash
docker run -d \
  -p 5050:5000 \
  -v redditvault-data:/data \
  -e REDDIT_CLIENT_ID=your_client_id \
  -e REDDIT_CLIENT_SECRET=your_client_secret \
  -e REDDIT_REDIRECT_URI=http://localhost:5050/auth/callback \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  ghcr.io/lukeevantech/redditvault:latest
```

### Run with Docker Compose

```yaml
services:
  redditvault:
    image: ghcr.io/lukeevantech/redditvault:latest
    ports:
      - "5050:5000"
    volumes:
      - ./data:/data
    environment:
      - REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
      - REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}
      - REDDIT_REDIRECT_URI=http://localhost:5050/auth/callback
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `REDDIT_CLIENT_ID` | Yes | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Yes | Reddit app client secret |
| `REDDIT_REDIRECT_URI` | Yes | OAuth callback URL |
| `SECRET_KEY` | Yes | Flask secret key (generate with `openssl rand -hex 32`) |
| `DATABASE_URL` | No | SQLite path (default: `sqlite:////data/reddit_saved.db`) |

## Development

```bash
# Clone
git clone https://github.com/LukeEvansTech/redditvault.git
cd redditvault

# Create .env
cp .env.example .env
# Edit .env with your Reddit credentials

# Run
docker-compose up --build
```

## License

MIT
