"""Tests for spawn tool delay-guard and cron action detection."""

import pytest

from nanobot.agent.tools.spawn import SpawnTool, _DELAY_PATTERN
from nanobot.agent.tools.cron import CronTool, _ACTION_PATTERNS


# ── Spawn delay guard ──────────────────────────────────────────────────


class TestSpawnDelayGuard:
    """Spawn must reject tasks that describe time delays."""

    @pytest.mark.parametrize("task", [
        "Wait 10 minutes then send an email",
        "Sleep 600 seconds and run the backup",
        "Send email in 10 minutes to user@example.com",
        "Do this after 5 minutes",
        "Run backup 30 seconds from now",
        "Execute script 2 hours later",
    ])
    def test_delay_detected(self, task: str):
        assert _DELAY_PATTERN.search(task), f"Should detect delay in: {task!r}"

    @pytest.mark.parametrize("task", [
        "Research the latest AI news",
        "Summarize this document for me",
        "Analyze the codebase and report findings",
        "Search for Python best practices",
    ])
    def test_no_false_positive(self, task: str):
        assert not _DELAY_PATTERN.search(task), f"Should NOT detect delay in: {task!r}"


# ── Cron action detection ──────────────────────────────────────────────


class TestCronActionDetection:
    """Cron auto-detect should distinguish agent tasks from user reminders."""

    @pytest.mark.parametrize("message", [
        "Send email to user@example.com with subject test",
        "Fetch the latest weather data",
        "Search for AI news and summarize",
        "Deploy the staging build",
        "Publish the blog post draft",
    ])
    def test_actionable(self, message: str):
        assert _ACTION_PATTERNS.search(message), f"Should be actionable: {message!r}"

    @pytest.mark.parametrize("message", [
        "Time to go to the gym!",
        "Take the dog out for a walk",
        "Check on the laundry",
        "Remember to call mom",
        "Pick up groceries",
        "Read the chapter for class",
        "stretch",
    ])
    def test_not_actionable(self, message: str):
        assert not _ACTION_PATTERNS.search(message), f"Should NOT be actionable: {message!r}"
