# RedditVault (redditsaveditems)

A Flask webapp plus a set of standalone scripts for exporting, categorizing, and bulk-unsaving Reddit "saved" posts/comments. The webapp (`webapp/`) does OAuth login, syncs saved items into SQLite, and serves a glassmorphism UI for browsing/searching/marking items reviewed. Alongside it are one-off CLI scripts for exporting saved items to JSON/Markdown, auto-categorizing them, and bulk-unsaving via OAuth, 1Password-stored credentials, or a standalone script.

Status: active, last commit 2026-01-15 (feat: add unsave functionality).

## Key files / entry points

- `webapp/` — Flask app: `auth.py` (Reddit OAuth), `sync.py` (pulls saved items), `models.py`, `categories.py`, `config.py`.
- `export_saved.py` / `export_markdown.py` — export saved items to `saved_items.json` / `markdown/*.md` by category.
- `categorize.py` — assigns categories, produces `saved_items_categorized.json`.
- `bulk_unsave*.py` (`.py`, `_oauth.py`, `_1password.py`, `_standalone.py`) — several variants of a script to unsave items from Reddit; only one is likely current, check dates before using.
- `duplicates_to_unsave.md`, `services_to_review.md` — working notes generated from the data, not source.
- `Dockerfile`, `docker-compose.yml` — container build/run for the webapp.
- `saved_items.json`, `saved_items_categorized.json` — exported data snapshots (large, not meant to be edited by hand).

## Commands

```bash
docker-compose up --build   # run the webapp
python export_saved.py      # export saved items to JSON
python categorize.py        # categorize exported items
python bulk_unsave.py       # unsave items (see other bulk_unsave_* variants)
```
