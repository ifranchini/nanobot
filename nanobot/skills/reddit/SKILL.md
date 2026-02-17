---
name: reddit
description: "Search and browse Reddit posts, comments, and subreddits. Use when: (1) the user mentions Reddit, (2) searching for community discussions, opinions, or experiences on technical topics, (3) looking for recommendations or real-world feedback."
metadata: {"nanobot":{"emoji":"🔗","requires":{"bins":["python3"]}}}
---

# Reddit

Browse and search Reddit using the public JSON API. No API keys or authentication required.

## Commands

The script is at `{baseDir}/scripts/reddit.py` (relative to this SKILL.md file).

Search across Reddit or within a subreddit:
```bash
python3 {baseDir}/scripts/reddit.py search "python async frameworks" --limit 5
python3 {baseDir}/scripts/reddit.py search "best LLM" --subreddit LocalLLaMA --sort top --time month --limit 5
```

Browse a subreddit:
```bash
python3 {baseDir}/scripts/reddit.py subreddit LocalLLaMA --sort hot --limit 10
python3 {baseDir}/scripts/reddit.py subreddit Python --sort top --limit 5
```

Fetch a specific post (by ID or URL):
```bash
python3 {baseDir}/scripts/reddit.py post abc123
python3 {baseDir}/scripts/reddit.py post "https://www.reddit.com/r/Python/comments/abc123/some_title/"
```

Read comments on a post:
```bash
python3 {baseDir}/scripts/reddit.py comments abc123 --limit 15 --sort best
```

## Useful Subreddits

| Topic | Subreddits |
|-------|-----------|
| AI/LLMs | LocalLLaMA, MachineLearning, artificial, ChatGPT |
| Programming | programming, Python, golang, rust, webdev |
| DevOps | devops, selfhosted, homelab, docker |
| Tech | technology, linux, sysadmin |

## Tips

- Use `--sort top --time week` to find the best recent content
- Search within a specific subreddit with `--subreddit NAME` for more focused results
- Post IDs and full Reddit URLs both work for the `post` and `comments` commands
- Comments are shown with indentation to indicate reply threading
- Rate limited to 1 request per 2 seconds (Reddit's public API limit)
