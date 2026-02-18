"""Tests for pure functions in skill scripts (Reddit, Google Workspace).

Scripts are loaded via importlib since they're standalone CLIs, not in the package namespace.
"""

import base64
import importlib.util
import sys
from pathlib import Path

import pytest

# ── Load scripts as modules ─────────────────────────────────────────────

REDDIT_SCRIPT = Path(__file__).parent.parent / "nanobot/skills/reddit/scripts/reddit.py"
GWORKSPACE_SCRIPT = (
    Path(__file__).parent.parent / "nanobot/skills/google-workspace/scripts/google_workspace.py"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


reddit = _load_module("reddit_script", REDDIT_SCRIPT)
gws = _load_module("gworkspace_script", GWORKSPACE_SCRIPT)


# ── Reddit: _clean_html ─────────────────────────────────────────────────


class TestCleanHtml:

    def test_strips_tags(self):
        assert reddit._clean_html("<p>hello</p>") == "hello"

    def test_unescapes_entities(self):
        # Note: _clean_html strips tags after unescaping, so &lt;/&gt; become < > then get stripped
        assert reddit._clean_html("&amp;") == "&"
        assert reddit._clean_html("it&#39;s") == "it's"

    def test_collapses_newlines(self):
        result = reddit._clean_html("a\n\n\n\nb")
        assert "\n\n\n" not in result
        assert "a" in result and "b" in result

    def test_empty_string(self):
        assert reddit._clean_html("") == ""


# ── Reddit: _parse_entries ───────────────────────────────────────────────


ATOM_NS = "http://www.w3.org/2005/Atom"

SAMPLE_FEED = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="{ATOM_NS}">
  <entry>
    <title>Post 1</title>
    <link href="https://reddit.com/r/test/1"/>
    <author><name>user1</name></author>
    <updated>2025-01-15T12:00:00Z</updated>
    <content type="html">&lt;p&gt;content1&lt;/p&gt;</content>
  </entry>
  <entry>
    <title>Post 2</title>
    <link href="https://reddit.com/r/test/2"/>
    <author><name>user2</name></author>
    <updated>2025-01-14T12:00:00Z</updated>
    <content type="html">&lt;p&gt;content2&lt;/p&gt;</content>
  </entry>
  <entry>
    <title>Post 3</title>
    <link href="https://reddit.com/r/test/3"/>
    <updated>2025-01-13T12:00:00Z</updated>
  </entry>
</feed>"""


class TestParseEntries:
    import xml.etree.ElementTree as ET

    @pytest.fixture
    def root(self):
        return self.ET.fromstring(SAMPLE_FEED)

    def test_parses_atom_feed(self, root):
        posts = reddit._parse_entries(root, limit=10)
        assert len(posts) == 3
        assert posts[0]["title"] == "Post 1"
        assert posts[0]["author"] == "user1"
        assert posts[0]["link"] == "https://reddit.com/r/test/1"

    def test_respects_limit(self, root):
        posts = reddit._parse_entries(root, limit=1)
        assert len(posts) == 1

    def test_handles_missing_fields(self, root):
        posts = reddit._parse_entries(root, limit=10)
        # Post 3 has no author
        assert posts[2]["author"] == ""


# ── Reddit: _extract_post_id ────────────────────────────────────────────


class TestExtractPostId:

    def test_bare_id(self):
        assert reddit._extract_post_id("abc123") == "abc123"

    def test_full_url(self):
        url = "https://www.reddit.com/r/python/comments/xyz789/some_title/"
        assert reddit._extract_post_id(url) == "xyz789"

    def test_url_no_trailing_slash(self):
        url = "https://www.reddit.com/r/python/comments/xyz789/some_title"
        assert reddit._extract_post_id(url) == "xyz789"


# ── Reddit: _format_post ────────────────────────────────────────────────


class TestFormatPost:

    def test_contains_title_author_link(self):
        post = {
            "title": "My Post",
            "author": "testuser",
            "updated": "2025-01-01",
            "link": "https://reddit.com/r/test/1",
            "content": "short body",
        }
        result = reddit._format_post(post)
        assert "My Post" in result
        assert "testuser" in result
        assert "https://reddit.com/r/test/1" in result

    def test_truncation_without_verbose(self):
        post = {
            "title": "Long",
            "author": "",
            "updated": "",
            "link": "",
            "content": "x" * 600,
        }
        result = reddit._format_post(post, verbose=False)
        assert result.endswith("...")
        assert len(result) < 700

    def test_no_truncation_with_verbose(self):
        post = {
            "title": "Long",
            "author": "",
            "updated": "",
            "link": "",
            "content": "x" * 600,
        }
        result = reddit._format_post(post, verbose=True)
        assert "..." not in result


# ── Google Workspace: _decode_body ───────────────────────────────────────


class TestDecodeBody:

    def test_simple_base64_body(self):
        text = "Hello, World!"
        encoded = base64.urlsafe_b64encode(text.encode()).decode()
        payload = {"body": {"data": encoded}}
        assert gws._decode_body(payload) == text

    def test_multipart_text_plain(self):
        text = "plain text body"
        encoded = base64.urlsafe_b64encode(text.encode()).decode()
        payload = {
            "body": {},
            "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded}},
            ],
        }
        assert gws._decode_body(payload) == text

    def test_html_fallback(self):
        html = "<p>hello</p>"
        encoded = base64.urlsafe_b64encode(html.encode()).decode()
        payload = {
            "body": {},
            "parts": [
                {"mimeType": "text/html", "body": {"data": encoded}},
            ],
        }
        result = gws._decode_body(payload)
        assert "hello" in result
        assert "<p>" not in result  # HTML tags stripped

    def test_nested_parts(self):
        text = "nested content"
        encoded = base64.urlsafe_b64encode(text.encode()).decode()
        payload = {
            "body": {},
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "body": {},
                    "parts": [
                        {"mimeType": "text/plain", "body": {"data": encoded}},
                    ],
                },
            ],
        }
        assert gws._decode_body(payload) == text

    def test_empty_payload(self):
        result = gws._decode_body({"body": {}, "parts": []})
        assert result == "(No text content)"


# ── Google Workspace: _get_header ────────────────────────────────────────


class TestGetHeader:

    def test_finds_case_insensitively(self):
        headers = [{"name": "Subject", "value": "Test Email"}]
        assert gws._get_header(headers, "subject") == "Test Email"

    def test_missing_returns_empty(self):
        headers = [{"name": "From", "value": "a@b.com"}]
        assert gws._get_header(headers, "Subject") == ""


# ── Google Workspace: _detect_timezone ───────────────────────────────────


class TestDetectTimezone:

    def test_returns_non_empty(self):
        result = gws._detect_timezone()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_to_utc_on_error(self, monkeypatch):
        from unittest.mock import patch

        with patch.object(gws, "datetime") as mock_dt:
            mock_dt.now.side_effect = RuntimeError("no tz")
            # Re-run the function with the patched datetime
            # Since _detect_timezone calls datetime.now(), patching the module-level ref works
            result = gws._detect_timezone()
            assert result == "UTC"


# ── Google Workspace: _get_creds_dir ─────────────────────────────────────


class TestGetCredsDir:

    def test_default_path(self):
        class FakeArgs:
            creds_dir = None
        result = gws._get_creds_dir(FakeArgs())
        assert ".nanobot" in result
        assert "google-credentials" in result

    def test_override(self):
        class FakeArgs:
            creds_dir = "/custom/path"
        assert gws._get_creds_dir(FakeArgs()) == "/custom/path"
