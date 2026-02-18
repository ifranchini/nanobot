"""Tests for nanobot/agent/tools/cron.py — agent-facing cron tool."""

from pathlib import Path
from unittest.mock import patch

import pytest

from nanobot.agent.tools.cron import CronTool
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule


@pytest.fixture
def cron_tool(tmp_cron_store: Path) -> CronTool:
    """CronTool with tmp store and session context set."""
    svc = CronService(store_path=tmp_cron_store)
    tool = CronTool(svc)
    tool.set_context(channel="telegram", chat_id="12345")
    return tool


# ── Add Job ──────────────────────────────────────────────────────────────


class TestCronToolAddJob:

    async def test_every_seconds(self, cron_tool: CronTool):
        with patch.object(cron_tool._cron, "_arm_timer"):
            result = await cron_tool.execute(
                action="add", message="check in", every_seconds=300
            )
        assert "Created job" in result
        jobs = cron_tool._cron.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].schedule.kind == "every"
        assert jobs[0].schedule.every_ms == 300_000

    async def test_cron_expr_with_tz(self, cron_tool: CronTool):
        with patch.object(cron_tool._cron, "_arm_timer"):
            result = await cron_tool.execute(
                action="add",
                message="daily standup",
                cron_expr="0 9 * * *",
                tz="America/New_York",
            )
        assert "Created job" in result
        jobs = cron_tool._cron.list_jobs()
        assert jobs[0].schedule.kind == "cron"
        assert jobs[0].schedule.expr == "0 9 * * *"
        assert jobs[0].schedule.tz == "America/New_York"

    async def test_at_with_iso_offset(self, cron_tool: CronTool):
        with patch.object(cron_tool._cron, "_arm_timer"):
            result = await cron_tool.execute(
                action="add",
                message="reminder",
                at="2099-06-15T10:30:00-08:00",
            )
        assert "Created job" in result
        jobs = cron_tool._cron.list_jobs()
        assert jobs[0].schedule.kind == "at"
        assert jobs[0].schedule.at_ms is not None

    async def test_naive_at_with_tz_localizes_correctly(self, cron_tool: CronTool):
        """REGRESSION: naive datetime + tz should localize to that timezone, not UTC."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        naive_str = "2099-06-15T10:30:00"
        tz_str = "America/Los_Angeles"

        with patch.object(cron_tool._cron, "_arm_timer"):
            result = await cron_tool.execute(
                action="add", message="tz test", at=naive_str, tz=tz_str
            )
        assert "Created job" in result

        jobs = cron_tool._cron.list_jobs()
        at_ms = jobs[0].schedule.at_ms

        # Expected: 2099-06-15T10:30:00 in America/Los_Angeles
        expected_dt = datetime(2099, 6, 15, 10, 30, tzinfo=ZoneInfo(tz_str))
        expected_ms = int(expected_dt.timestamp() * 1000)
        assert at_ms == expected_ms

    async def test_missing_message_error(self, cron_tool: CronTool):
        result = await cron_tool.execute(action="add", message="", every_seconds=60)
        assert "Error" in result
        assert "message" in result.lower()

    async def test_no_context_error(self, tmp_cron_store: Path):
        svc = CronService(store_path=tmp_cron_store)
        tool = CronTool(svc)
        # No set_context called
        result = await tool.execute(action="add", message="hello", every_seconds=60)
        assert "Error" in result
        assert "context" in result.lower()

    async def test_invalid_tz_error(self, cron_tool: CronTool):
        result = await cron_tool.execute(
            action="add", message="bad tz", every_seconds=60, tz="Mars/Olympus"
        )
        assert "Error" in result
        assert "timezone" in result.lower()

    async def test_at_sets_delete_after_run(self, cron_tool: CronTool):
        with patch.object(cron_tool._cron, "_arm_timer"):
            await cron_tool.execute(
                action="add", message="one-shot", at="2099-01-01T00:00:00+00:00"
            )
        jobs = cron_tool._cron.list_jobs()
        assert jobs[0].delete_after_run is True

    async def test_no_schedule_type_error(self, cron_tool: CronTool):
        result = await cron_tool.execute(action="add", message="no schedule")
        assert "Error" in result


# ── List Jobs ────────────────────────────────────────────────────────────


class TestCronToolListJobs:

    async def test_empty(self, cron_tool: CronTool):
        result = await cron_tool.execute(action="list")
        assert "No scheduled jobs" in result

    async def test_with_jobs(self, cron_tool: CronTool):
        with patch.object(cron_tool._cron, "_arm_timer"):
            await cron_tool.execute(
                action="add", message="daily check", every_seconds=86400
            )
        result = await cron_tool.execute(action="list")
        assert "daily check" in result
        assert "Scheduled jobs" in result

    async def test_cron_shows_expr_and_tz(self, cron_tool: CronTool):
        with patch.object(cron_tool._cron, "_arm_timer"):
            await cron_tool.execute(
                action="add",
                message="standup",
                cron_expr="0 9 * * 1-5",
                tz="Europe/Rome",
            )
        result = await cron_tool.execute(action="list")
        assert "0 9 * * 1-5" in result
        assert "Europe/Rome" in result


# ── Remove Job ───────────────────────────────────────────────────────────


class TestCronToolRemoveJob:

    async def test_remove_existing(self, cron_tool: CronTool):
        with patch.object(cron_tool._cron, "_arm_timer"):
            await cron_tool.execute(
                action="add", message="temp", every_seconds=60
            )
        job_id = cron_tool._cron.list_jobs()[0].id
        result = await cron_tool.execute(action="remove", job_id=job_id)
        assert "Removed" in result

    async def test_remove_missing(self, cron_tool: CronTool):
        result = await cron_tool.execute(action="remove", job_id="nope")
        assert "not found" in result

    async def test_remove_no_job_id_error(self, cron_tool: CronTool):
        result = await cron_tool.execute(action="remove")
        assert "Error" in result
