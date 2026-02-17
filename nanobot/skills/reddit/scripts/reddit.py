#!/usr/bin/env python3
"""Reddit browser using public RSS feeds. No authentication required."""

import argparse
import html
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

USER_AGENT = "nanobot-reddit-skill/1.0 (read-only browser)"
BASE_URL = "https://www.reddit.com"
NS = {"atom": "http://www.w3.org/2005/Atom"}
_last_request = 0.0


def _fetch_rss(url: str) -> ET.Element:
    """Fetch and parse an RSS/Atom feed from Reddit."""
    global _last_request
    elapsed = time.monotonic() - _last_request
    if elapsed < 2.0:
        time.sleep(2.0 - elapsed)

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            _last_request = time.monotonic()
            return ET.fromstring(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Error: not found — {url}", file=sys.stderr)
        elif e.code == 429:
            print("Error: rate limited by Reddit. Try again later.", file=sys.stderr)
        elif e.code == 403:
            print("Error: access denied. Subreddit may be private.", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.code} — {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: could not connect — {e.reason}", file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error: failed to parse feed — {e}", file=sys.stderr)
        sys.exit(1)


def _clean_html(raw: str) -> str:
    """Strip HTML tags and decode entities."""
    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_entries(root: ET.Element, limit: int) -> list[dict]:
    """Parse Atom feed entries into post dicts."""
    entries = root.findall("atom:entry", NS)[:limit]
    posts = []
    for entry in entries:
        title = entry.findtext("atom:title", "", NS)
        link_el = entry.find("atom:link", NS)
        link = link_el.get("href", "") if link_el is not None else ""
        author = entry.findtext("atom:author/atom:name", "", NS)
        updated = entry.findtext("atom:updated", "", NS)
        content_el = entry.find("atom:content", NS)
        content = content_el.text if content_el is not None and content_el.text else ""

        posts.append(
            {
                "title": title,
                "link": link,
                "author": author,
                "updated": updated[:10] if updated else "",
                "content": content,
            }
        )
    return posts


def _format_post(post: dict, verbose: bool = False) -> str:
    """Format a single post for display."""
    lines = []
    lines.append(f"## {post['title']}")
    meta = []
    if post["author"]:
        meta.append(post["author"])
    if post["updated"]:
        meta.append(post["updated"])
    if meta:
        lines.append(" | ".join(meta))
    if post["link"]:
        lines.append(post["link"])

    if post["content"]:
        text = _clean_html(post["content"])
        if not verbose and len(text) > 500:
            text = text[:500] + "..."
        if text:
            lines.append("")
            lines.append(text)

    return "\n".join(lines)


def _extract_post_id(id_or_url: str) -> str:
    """Extract a post ID from a URL or return as-is."""
    if "/" in id_or_url:
        parts = id_or_url.rstrip("/").split("/")
        try:
            idx = parts.index("comments")
            return parts[idx + 1]
        except (ValueError, IndexError):
            pass
    return id_or_url


def cmd_search(args):
    """Search Reddit via RSS."""
    params = {"q": args.query, "sort": args.sort, "t": args.time, "type": "link"}
    if args.subreddit:
        params["restrict_sr"] = "on"
        url = f"{BASE_URL}/r/{args.subreddit}/search.rss?{urllib.parse.urlencode(params)}"
    else:
        url = f"{BASE_URL}/search.rss?{urllib.parse.urlencode(params)}"

    root = _fetch_rss(url)
    posts = _parse_entries(root, args.limit)

    if not posts:
        print("No results found.")
        return

    print(f"Found {len(posts)} results for '{args.query}':\n")
    for post in posts:
        print(_format_post(post))
        print()


def cmd_subreddit(args):
    """Browse a subreddit via RSS."""
    params = {}
    if args.sort == "top":
        params["t"] = args.time

    url = f"{BASE_URL}/r/{args.name}/{args.sort}.rss"
    if params:
        url += f"?{urllib.parse.urlencode(params)}"

    root = _fetch_rss(url)
    posts = _parse_entries(root, args.limit)

    if not posts:
        print(f"No posts found in r/{args.name}.")
        return

    feed_title = root.findtext("atom:title", "", NS)
    print(f"# {feed_title or 'r/' + args.name}\n")

    for post in posts:
        print(_format_post(post))
        print()


def cmd_post(args):
    """Fetch a single post via RSS."""
    post_id = _extract_post_id(args.post_id)
    url = f"{BASE_URL}/comments/{post_id}.rss"

    root = _fetch_rss(url)
    posts = _parse_entries(root, 1)

    if not posts:
        print("Error: post not found.", file=sys.stderr)
        sys.exit(1)

    print(_format_post(posts[0], verbose=True))


def cmd_comments(args):
    """Fetch comments for a post via RSS."""
    post_id = _extract_post_id(args.post_id)
    url = f"{BASE_URL}/comments/{post_id}.rss"

    root = _fetch_rss(url)
    entries = root.findall("atom:entry", NS)

    if not entries:
        print("Error: post not found.", file=sys.stderr)
        sys.exit(1)

    # First entry is the post, rest are comments
    post = _parse_entries(root, 1)
    if post:
        print(f"## {post[0]['title']}")
        if post[0]["link"]:
            print(post[0]["link"])
        print()

    comment_entries = entries[1 : args.limit + 1]
    if not comment_entries:
        print("No comments found.")
        return

    print(f"### Comments ({len(comment_entries)} shown)\n")
    for entry in comment_entries:
        author = entry.findtext("atom:author/atom:name", "[deleted]", NS)
        content_el = entry.find("atom:content", NS)
        body = ""
        if content_el is not None and content_el.text:
            body = _clean_html(content_el.text)
            if len(body) > 400:
                body = body[:400] + "..."

        print(f"- **{author}**")
        if body:
            print(f"  {body}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Reddit browser via RSS (no auth required)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = subparsers.add_parser("search", help="Search Reddit for posts")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--subreddit", "-r", help="Limit search to a subreddit")
    p_search.add_argument(
        "--sort", choices=["relevance", "hot", "top", "new", "comments"], default="relevance"
    )
    p_search.add_argument(
        "--time", choices=["hour", "day", "week", "month", "year", "all"], default="all"
    )
    p_search.add_argument("--limit", "-n", type=int, default=10)

    # subreddit
    p_sub = subparsers.add_parser("subreddit", help="Browse a subreddit")
    p_sub.add_argument("name", help="Subreddit name (without r/)")
    p_sub.add_argument("--sort", choices=["hot", "new", "top", "rising"], default="hot")
    p_sub.add_argument(
        "--time",
        choices=["hour", "day", "week", "month", "year", "all"],
        default="week",
        help="Time filter (for --sort top)",
    )
    p_sub.add_argument("--limit", "-n", type=int, default=10)

    # post
    p_post = subparsers.add_parser("post", help="Fetch a single post by ID or URL")
    p_post.add_argument("post_id", help="Post ID or full Reddit URL")

    # comments
    p_comments = subparsers.add_parser("comments", help="Fetch comments for a post")
    p_comments.add_argument("post_id", help="Post ID or full Reddit URL")
    p_comments.add_argument("--limit", "-n", type=int, default=20)

    args = parser.parse_args()

    commands = {
        "search": cmd_search,
        "subreddit": cmd_subreddit,
        "post": cmd_post,
        "comments": cmd_comments,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
