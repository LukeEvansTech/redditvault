#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Export categorized Reddit saved items to markdown files."""

import json
import os
import re


def slugify(text: str) -> str:
    """Convert text to a safe filename."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-')


def format_item(item: dict) -> str:
    """Format a single item as markdown."""
    lines = []

    if item["type"] == "post":
        title = item.get("title", "Untitled")
        lines.append(f"### [{title}]({item['permalink']})")
        lines.append(f"**r/{item['subreddit']}** · {item['score']} points · by u/{item['author']}")
        lines.append(f"*{item['created_utc'][:10]}*")

        if item.get("is_self") and item.get("selftext"):
            # Self post with text
            text = item["selftext"][:300]
            if len(item.get("selftext", "")) > 300:
                text += "..."
            lines.append(f"\n> {text}")
        elif not item.get("is_self"):
            # Link post
            lines.append(f"\n🔗 {item['url']}")
    else:
        # Comment
        lines.append(f"### [Comment on: {item.get('post_title', 'Unknown post')}]({item['permalink']})")
        lines.append(f"**r/{item['subreddit']}** · {item['score']} points · by u/{item['author']}")
        lines.append(f"*{item['created_utc'][:10]}*")

        if item.get("body"):
            body = item["body"][:300]
            if len(item.get("body", "")) > 300:
                body += "..."
            lines.append(f"\n> {body}")

    return "\n".join(lines)


def main():
    # Create output directory
    os.makedirs("markdown", exist_ok=True)

    # Load categorized items
    with open("saved_items_categorized.json") as f:
        categorized = json.load(f)

    # Create index file
    index_lines = ["# Reddit Saved Items\n"]
    index_lines.append(f"Total: {sum(len(items) for items in categorized.values())} items\n")
    index_lines.append("## Categories\n")

    # Sort categories by item count
    sorted_categories = sorted(categorized.items(), key=lambda x: -len(x[1]))

    for category, items in sorted_categories:
        slug = slugify(category)
        index_lines.append(f"- [{category}]({slug}.md) ({len(items)} items)")

    with open("markdown/README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    # Create category files
    for category, items in sorted_categories:
        slug = slugify(category)
        lines = [f"# {category}\n"]
        lines.append(f"{len(items)} saved items\n")
        lines.append("[← Back to Index](README.md)\n")
        lines.append("---\n")

        # Group by subreddit within category
        by_subreddit = {}
        for item in items:
            sub = item["subreddit"]
            if sub not in by_subreddit:
                by_subreddit[sub] = []
            by_subreddit[sub].append(item)

        # Sort subreddits by count
        for subreddit, sub_items in sorted(by_subreddit.items(), key=lambda x: -len(x[1])):
            lines.append(f"\n## r/{subreddit} ({len(sub_items)})\n")

            # Sort items by date (newest first)
            sub_items.sort(key=lambda x: x.get("created_utc", ""), reverse=True)

            for item in sub_items:
                lines.append(format_item(item))
                lines.append("\n---\n")

        with open(f"markdown/{slug}.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"Created: markdown/{slug}.md ({len(items)} items)")

    print(f"\nCreated markdown/README.md (index)")
    print(f"Total: {len(sorted_categories)} category files")


if __name__ == "__main__":
    main()
