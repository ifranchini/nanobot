#!/usr/bin/env python3
"""Reddit browser using the public JSON API. No authentication required."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "nanobot-reddit-skill/1.0 (read-only browser)"
BASE_URL = "https://www.reddit.com"
# Respect Reddit's rate limit: 1 request per 2 seconds for unauthenticated
_last_request = 0.0


def _fetch(url: str) -> dict:
    """Fetch a Reddit JSON endpoint with rate limiting and error handling."""
    global _last_request
    elapsed = time.monotonic() - _last_request
    if elapsed < 2.0:
        time.sleep(2.0 - elapsed)

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            _last_request = time.monotonic()
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Error: not found — {url}", file=sys.stderr)
        elif e.code == 429:
            print("Error: rate limited by Reddit. Try again in a few seconds.", file=sys.stderr)
        elif e.code == 403:
            print("Error: subreddit is private or quarantined.", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.code} — {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: could not connect to Reddit — {e.reason}", file=sys.stderr)
        sys.exit(1)


def extract_post_id(id_or_url: str) -> str:
    """Extract a post ID from a URL or return the ID as-is."""
    if "/" in id_or_url:
        parts = id_or_url.rstrip("/").split("/")
        try:
            idx = parts.index("comments")
            return parts[idx + 1]
        except (ValueError, IndexError):
            pass
    return id_or_url


def format_post(post: dict, verbose: bool = False) -> str:
    """Format a single post for display."""
    d = post["data"] if "data" in post else post
    lines = []

    flair = f" [{d['link_flair_text']}]" if d.get("link_flair_text") else ""
    lines.append(f"## {d['title']}{flair}")
    author = d.get("author", "[deleted]")
    sub = d.get("subreddit", "?")
    lines.append(
        f"r/{sub} | {d.get('score', 0)} pts | {d.get('num_comments', 0)} comments | u/{author}"
    )
    lines.append(f"https://reddit.com{d.get('permalink', '')}")

    selftext = d.get("selftext", "")
    is_self = d.get("is_self", False)
    if is_self and selftext:
        text = selftext
        if not verbose and len(text) > 500:
            text = text[:500] + "..."
        lines.append("")
        lines.append(text)
    elif not is_self and d.get("url"):
        lines.append(f"Link: {d['url']}")

    return "\n".join(lines)


def cmd_search(args):
    """Search Reddit for posts."""
    params = {
        "q": args.query,
        "sort": args.sort,
        "t": args.time,
        "limit": str(args.limit),
        "restrict_sr": "",
        "type": "link",
    }

    if args.subreddit:
        params["restrict_sr"] = "on"
        url = f"{BASE_URL}/r/{args.subreddit}/search.json?{urllib.parse.urlencode(params)}"
    else:
        url = f"{BASE_URL}/search.json?{urllib.parse.urlencode(params)}"

    data = _fetch(url)
    posts = data.get("data", {}).get("children", [])

    if not posts:
        print("No results found.")
        return

    print(f"Found {len(posts)} results for '{args.query}':\n")
    for post in posts:
        print(format_post(post))
        print()


def cmd_post(args):
    """Fetch a single post by ID or URL."""
    post_id = extract_post_id(args.post_id)
    url = f"{BASE_URL}/comments/{post_id}.json?limit=0"
    data = _fetch(url)

    if not isinstance(data, list) or not data:
        print("Error: unexpected response format.", file=sys.stderr)
        sys.exit(1)

    posts = data[0].get("data", {}).get("children", [])
    if not posts:
        print("Error: post not found.", file=sys.stderr)
        sys.exit(1)

    print(format_post(posts[0], verbose=True))


def cmd_comments(args):
    """Fetch comments for a post."""
    post_id = extract_post_id(args.post_id)
    sort = args.sort
    url = f"{BASE_URL}/comments/{post_id}.json?sort={sort}&limit={args.limit}"
    data = _fetch(url)

    if not isinstance(data, list) or len(data) < 2:
        print("Error: unexpected response format.", file=sys.stderr)
        sys.exit(1)

    # Print post header
    posts = data[0].get("data", {}).get("children", [])
    if posts:
        d = posts[0]["data"]
        print(f"## {d['title']}")
        print(
            f"r/{d.get('subreddit', '?')} | {d.get('score', 0)} pts"
            f" | {d.get('num_comments', 0)} comments\n"
        )

    # Print comments
    comments = data[1].get("data", {}).get("children", [])
    count = [0]

    def print_comment(comment, depth=0):
        if count[0] >= args.limit:
            return
        if comment.get("kind") != "t1":
            return
        cd = comment["data"]
        count[0] += 1

        indent = "  " * depth
        author = cd.get("author", "[deleted]")
        body = cd.get("body", "")
        body = body.replace("\n", f"\n{indent}  ")
        if len(body) > 400:
            body = body[:400] + "..."

        print(f"{indent}- **u/{author}** ({cd.get('score', 0)} pts)")
        print(f"{indent}  {body}")
        print()

        replies = cd.get("replies")
        if isinstance(replies, dict):
            for reply in replies.get("data", {}).get("children", []):
                if count[0] >= args.limit:
                    return
                print_comment(reply, depth + 1)

    for comment in comments:
        if count[0] >= args.limit:
            break
        print_comment(comment)


def cmd_subreddit(args):
    """Browse a subreddit's posts."""
    sort = args.sort
    url = f"{BASE_URL}/r/{args.name}/{sort}.json?limit={args.limit}"
    data = _fetch(url)

    posts = data.get("data", {}).get("children", [])
    if not posts:
        print(f"No posts found in r/{args.name}.")
        return

    # Try to get subreddit info
    about_url = f"{BASE_URL}/r/{args.name}/about.json"
    try:
        about = _fetch(about_url)
        info = about.get("data", {})
        desc = info.get("public_description", "")
        subscribers = info.get("subscribers", 0)
        display_name = info.get("display_name", args.name)
        if desc:
            if len(desc) > 200:
                desc = desc[:200] + "..."
            print(f"# r/{display_name} ({subscribers:,} members)")
            print(f"{desc}\n")
        else:
            print(f"# r/{display_name} ({subscribers:,} members)\n")
    except SystemExit:
        print(f"# r/{args.name}\n")

    for post in posts:
        print(format_post(post))
        print()


def main():
    parser = argparse.ArgumentParser(description="Reddit browser (read-only, no auth required)")
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

    # post
    p_post = subparsers.add_parser("post", help="Fetch a single post by ID or URL")
    p_post.add_argument("post_id", help="Post ID or full Reddit URL")

    # comments
    p_comments = subparsers.add_parser("comments", help="Fetch comments for a post")
    p_comments.add_argument("post_id", help="Post ID or full Reddit URL")
    p_comments.add_argument("--limit", "-n", type=int, default=20)
    p_comments.add_argument(
        "--sort", choices=["best", "top", "new", "controversial"], default="best"
    )

    # subreddit
    p_sub = subparsers.add_parser("subreddit", help="Browse a subreddit")
    p_sub.add_argument("name", help="Subreddit name (without r/)")
    p_sub.add_argument("--sort", choices=["hot", "new", "top", "rising"], default="hot")
    p_sub.add_argument("--limit", "-n", type=int, default=10)

    args = parser.parse_args()

    commands = {
        "search": cmd_search,
        "post": cmd_post,
        "comments": cmd_comments,
        "subreddit": cmd_subreddit,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
