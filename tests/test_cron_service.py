"""Tests for nanobot/cron/service.py — core cron logic."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from nanobot.cron.service import CronService, _compute_next_run
from nanobot.cron.types import CronJob, CronJobState, CronPayload, CronSchedule, CronStore


# ── _compute_next_run ────────────────────────────────────────────────────


class TestComputeNextRun:
    """Tests for the _compute_next_run() helper."""

    def test_at_future_returns_at_ms(self):
        sched = CronSchedule(kind="at", at_ms=2000)
        assert _compute_next_run(sched, now_ms=1000) == 2000

    def test_at_past_returns_none(self):
        sched = CronSchedule(kind="at", at_ms=500)
        assert _compute_next_run(sched, now_ms=1000) is None

    def test_at_none_at_ms_returns_none(self):
        sched = CronSchedule(kind="at", at_ms=None)
        assert _compute_next_run(sched, now_ms=1000) is None

    def test_every_returns_now_plus_interval(self):
        sched = CronSchedule(kind="every", every_ms=5000)
        assert _compute_next_run(sched, now_ms=1000) == 6000

    def test_every_zero_returns_none(self):
        sched = CronSchedule(kind="every", every_ms=0)
        assert _compute_next_run(sched, now_ms=1000) is None

    def test_every_none_returns_none(self):
        sched = CronSchedule(kind="every", every_ms=None)
        assert _compute_next_run(sched, now_ms=1000) is None

    def test_cron_valid_returns_future(self):
        sched = CronSchedule(kind="cron", expr="* * * * *")
        result = _compute_next_run(sched, now_ms=1_000_000_000_000)
        assert result is not None
        assert result > 1_000_000_000_000

    def test_cron_with_tz_differs_from_utc(self):
        now_ms = 1_700_000_000_000  # ~2023-11-14 UTC
        sched_utc = CronSchedule(kind="cron", expr="0 9 * * *", tz="UTC")
        sched_la = CronSchedule(kind="cron", expr="0 9 * * *", tz="America/Los_Angeles")
        result_utc = _compute_next_run(sched_utc, now_ms)
        result_la = _compute_next_run(sched_la, now_ms)
        assert result_utc is not None
        assert result_la is not None
        assert result_utc != result_la

    def test_cron_invalid_expr_returns_none(self):
        sched = CronSchedule(kind="cron", expr="not a cron")
        assert _compute_next_run(sched, now_ms=1000) is None


# ── Persistence ──────────────────────────────────────────────────────────


class TestCronPersistence:
    """Tests for _load_store / _save_store round-trip."""

    def test_round_trip(self, tmp_cron_store: Path):
        svc = CronService(store_path=tmp_cron_store)
        with patch.object(svc, "_arm_timer"):
            job = svc.add_job(
                name="test-job",
                schedule=CronSchedule(kind="every", every_ms=60_000),
                message="hello",
                deliver=True,
                channel="telegram",
                to="123",
            )

        # Force reload
        svc2 = CronService(store_path=tmp_cron_store)
        loaded = svc2._load_store()
        assert len(loaded.jobs) == 1
        j = loaded.jobs[0]
        assert j.id == job.id
        assert j.name == "test-job"
        assert j.schedule.kind == "every"
        assert j.schedule.every_ms == 60_000
        assert j.payload.message == "hello"
        assert j.payload.deliver is True
        assert j.payload.channel == "telegram"
        assert j.payload.to == "123"

    def test_camelcase_json_keys(self, tmp_cron_store: Path):
        svc = CronService(store_path=tmp_cron_store)
        with patch.object(svc, "_arm_timer"):
            svc.add_job(
                name="camel",
                schedule=CronSchedule(kind="at", at_ms=9999),
                message="m",
            )
        raw = json.loads(tmp_cron_store.read_text())
        job_data = raw["jobs"][0]
        assert "atMs" in job_data["schedule"]
        assert "everyMs" in job_data["schedule"]
        assert "nextRunAtMs" in job_data["state"]
        assert "createdAtMs" in job_data
        assert "deleteAfterRun" in job_data

    def test_missing_file_returns_empty(self, tmp_path: Path):
        svc = CronService(store_path=tmp_path / "nonexistent.json")
        store = svc._load_store()
        assert store.jobs == []

    def test_corrupt_json_returns_empty(self, tmp_cron_store: Path):
        tmp_cron_store.write_text("{bad json!!!")
        svc = CronService(store_path=tmp_cron_store)
        store = svc._load_store()
        assert store.jobs == []


# ── Job Execution ────────────────────────────────────────────────────────


class TestCronJobExecution:
    """Tests for _execute_job()."""

    @pytest.fixture
    def _make_service(self, tmp_cron_store: Path):
        def factory(on_job=None):
            cb = on_job or AsyncMock(return_value="ok")
            svc = CronService(store_path=tmp_cron_store, on_job=cb)
            svc._store = CronStore()
            return svc, cb
        return factory

    async def test_race_condition_next_run_none_during_callback(self, _make_service):
        """REGRESSION: next_run_at_ms must be None when on_job fires."""
        captured_state = {}

        async def spy(job: CronJob) -> str:
            captured_state["next_run_at_ms"] = job.state.next_run_at_ms
            return "done"

        svc, _ = _make_service(on_job=spy)
        job = CronJob(
            id="race-1",
            name="race-test",
            schedule=CronSchedule(kind="every", every_ms=60_000),
            state=CronJobState(next_run_at_ms=5000),
        )
        svc._store.jobs.append(job)

        await svc._execute_job(job)
        assert captured_state["next_run_at_ms"] is None

    async def test_oneshot_at_delete_after_run(self, _make_service):
        svc, _ = _make_service()
        job = CronJob(
            id="del-1",
            name="one-shot",
            schedule=CronSchedule(kind="at", at_ms=1000),
            state=CronJobState(next_run_at_ms=1000),
            delete_after_run=True,
        )
        svc._store.jobs.append(job)

        await svc._execute_job(job)
        assert all(j.id != "del-1" for j in svc._store.jobs)

    async def test_oneshot_at_no_delete_disables(self, _make_service):
        svc, _ = _make_service()
        job = CronJob(
            id="keep-1",
            name="keep-job",
            schedule=CronSchedule(kind="at", at_ms=1000),
            state=CronJobState(next_run_at_ms=1000),
            delete_after_run=False,
        )
        svc._store.jobs.append(job)

        await svc._execute_job(job)
        assert job.enabled is False
        assert job.state.next_run_at_ms is None

    async def test_recurring_every_recomputes_next_run(self, _make_service):
        svc, _ = _make_service()
        job = CronJob(
            id="rec-1",
            name="recurring",
            schedule=CronSchedule(kind="every", every_ms=30_000),
            state=CronJobState(next_run_at_ms=5000),
        )
        svc._store.jobs.append(job)

        await svc._execute_job(job)
        assert job.state.next_run_at_ms is not None
        assert job.state.next_run_at_ms > 0

    async def test_success_sets_ok_status(self, _make_service):
        svc, _ = _make_service()
        job = CronJob(
            id="ok-1",
            name="success",
            schedule=CronSchedule(kind="every", every_ms=10_000),
            state=CronJobState(next_run_at_ms=1000),
        )
        svc._store.jobs.append(job)

        await svc._execute_job(job)
        assert job.state.last_status == "ok"
        assert job.state.last_error is None

    async def test_error_sets_error_status(self, _make_service):
        async def failing_cb(job):
            raise RuntimeError("boom")

        svc, _ = _make_service(on_job=failing_cb)
        job = CronJob(
            id="err-1",
            name="failing",
            schedule=CronSchedule(kind="every", every_ms=10_000),
            state=CronJobState(next_run_at_ms=1000),
        )
        svc._store.jobs.append(job)

        await svc._execute_job(job)
        assert job.state.last_status == "error"
        assert "boom" in job.state.last_error


# ── CRUD ─────────────────────────────────────────────────────────────────


class TestCronCRUD:
    """Tests for add/remove/enable/list."""

    def test_add_job_creates_and_persists(self, tmp_cron_store: Path):
        svc = CronService(store_path=tmp_cron_store)
        with patch.object(svc, "_arm_timer"):
            job = svc.add_job(
                name="persist-me",
                schedule=CronSchedule(kind="every", every_ms=5000),
                message="test",
            )
        assert job.name == "persist-me"
        assert job.enabled is True
        assert job.payload.message == "test"
        assert tmp_cron_store.exists()

    def test_remove_job_existing(self, tmp_cron_store: Path):
        svc = CronService(store_path=tmp_cron_store)
        with patch.object(svc, "_arm_timer"):
            job = svc.add_job(
                name="to-remove",
                schedule=CronSchedule(kind="every", every_ms=1000),
                message="bye",
            )
            assert svc.remove_job(job.id) is True
        assert len(svc.list_jobs(include_disabled=True)) == 0

    def test_remove_job_missing(self, tmp_cron_store: Path):
        svc = CronService(store_path=tmp_cron_store)
        assert svc.remove_job("nonexistent") is False

    def test_enable_job_toggle(self, tmp_cron_store: Path):
        svc = CronService(store_path=tmp_cron_store)
        with patch.object(svc, "_arm_timer"):
            job = svc.add_job(
                name="toggle",
                schedule=CronSchedule(kind="every", every_ms=5000),
                message="m",
            )
            # Disable
            result = svc.enable_job(job.id, enabled=False)
            assert result is not None
            assert result.enabled is False
            assert result.state.next_run_at_ms is None

            # Re-enable
            result = svc.enable_job(job.id, enabled=True)
            assert result.enabled is True
            assert result.state.next_run_at_ms is not None

    def test_list_jobs_sorted_by_next_run(self, tmp_cron_store: Path):
        svc = CronService(store_path=tmp_cron_store)
        with patch.object(svc, "_arm_timer"):
            svc.add_job(
                name="later",
                schedule=CronSchedule(kind="every", every_ms=60_000),
                message="a",
            )
            svc.add_job(
                name="sooner",
                schedule=CronSchedule(kind="every", every_ms=1_000),
                message="b",
            )
        jobs = svc.list_jobs()
        assert len(jobs) == 2
        if jobs[0].state.next_run_at_ms and jobs[1].state.next_run_at_ms:
            assert jobs[0].state.next_run_at_ms <= jobs[1].state.next_run_at_ms

    def test_list_jobs_excludes_disabled(self, tmp_cron_store: Path):
        svc = CronService(store_path=tmp_cron_store)
        with patch.object(svc, "_arm_timer"):
            job = svc.add_job(
                name="will-disable",
                schedule=CronSchedule(kind="every", every_ms=5000),
                message="m",
            )
            svc.enable_job(job.id, enabled=False)
        assert len(svc.list_jobs()) == 0
        assert len(svc.list_jobs(include_disabled=True)) == 1
