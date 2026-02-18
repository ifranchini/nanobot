"""Tests for nanobot/agent/skills.py — SkillsLoader."""

import os
import shutil

import pytest

from nanobot.agent.skills import SkillsLoader


# ── _strip_frontmatter ──────────────────────────────────────────────────


class TestStripFrontmatter:

    @pytest.fixture
    def loader(self, tmp_path):
        return SkillsLoader(workspace=tmp_path)

    def test_strips_yaml_frontmatter(self, loader: SkillsLoader):
        content = "---\ntitle: Test\n---\n# Body\nContent here"
        result = loader._strip_frontmatter(content)
        assert result == "# Body\nContent here"

    def test_no_frontmatter(self, loader: SkillsLoader):
        content = "# Just markdown\nNo frontmatter"
        result = loader._strip_frontmatter(content)
        assert result == content

    def test_frontmatter_only(self, loader: SkillsLoader):
        content = "---\ntitle: Only FM\n---\n"
        result = loader._strip_frontmatter(content)
        assert result == ""


# ── _parse_nanobot_metadata ──────────────────────────────────────────────


class TestParseNanobotMetadata:

    @pytest.fixture
    def loader(self, tmp_path):
        return SkillsLoader(workspace=tmp_path)

    def test_parses_nanobot_key(self, loader: SkillsLoader):
        raw = '{"nanobot": {"always": true, "requires": {"bins": ["git"]}}}'
        result = loader._parse_nanobot_metadata(raw)
        assert result["always"] is True
        assert result["requires"]["bins"] == ["git"]

    def test_openclaw_fallback(self, loader: SkillsLoader):
        raw = '{"openclaw": {"always": false}}'
        result = loader._parse_nanobot_metadata(raw)
        assert result["always"] is False

    def test_nanobot_takes_precedence(self, loader: SkillsLoader):
        raw = '{"nanobot": {"always": true}, "openclaw": {"always": false}}'
        result = loader._parse_nanobot_metadata(raw)
        assert result["always"] is True

    def test_invalid_json(self, loader: SkillsLoader):
        assert loader._parse_nanobot_metadata("{bad}") == {}

    def test_none_input(self, loader: SkillsLoader):
        assert loader._parse_nanobot_metadata(None) == {}

    def test_non_dict_input(self, loader: SkillsLoader):
        assert loader._parse_nanobot_metadata('"just a string"') == {}


# ── _check_requirements ─────────────────────────────────────────────────


class TestCheckRequirements:

    @pytest.fixture
    def loader(self, tmp_path):
        return SkillsLoader(workspace=tmp_path)

    def test_empty_requires_passes(self, loader: SkillsLoader):
        assert loader._check_requirements({}) is True
        assert loader._check_requirements({"requires": {}}) is True

    def test_bins_found(self, loader: SkillsLoader, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/" + x)
        meta = {"requires": {"bins": ["python3", "git"]}}
        assert loader._check_requirements(meta) is True

    def test_bins_missing(self, loader: SkillsLoader, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: None)
        meta = {"requires": {"bins": ["nonexistent_tool"]}}
        assert loader._check_requirements(meta) is False

    def test_env_present(self, loader: SkillsLoader, monkeypatch):
        monkeypatch.setenv("MY_TEST_KEY", "value")
        meta = {"requires": {"env": ["MY_TEST_KEY"]}}
        assert loader._check_requirements(meta) is True

    def test_env_missing(self, loader: SkillsLoader, monkeypatch):
        monkeypatch.delenv("MY_TEST_KEY_MISSING", raising=False)
        meta = {"requires": {"env": ["MY_TEST_KEY_MISSING"]}}
        assert loader._check_requirements(meta) is False

    def test_mixed_requirements(self, loader: SkillsLoader, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/" + x)
        monkeypatch.delenv("MISSING_ENV_VAR", raising=False)
        meta = {"requires": {"bins": ["python3"], "env": ["MISSING_ENV_VAR"]}}
        assert loader._check_requirements(meta) is False
