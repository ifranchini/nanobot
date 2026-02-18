"""Shared fixtures for nanobot tests."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from nanobot.cron.service import CronService


@pytest.fixture
def tmp_cron_store(tmp_path: Path) -> Path:
    """Temp path for cron JSON persistence."""
    return tmp_path / "cron_store.json"


@pytest.fixture
def cron_service(tmp_cron_store: Path) -> CronService:
    """CronService with tmp store and mock on_job callback."""
    cb = AsyncMock(return_value=None)
    svc = CronService(store_path=tmp_cron_store, on_job=cb)
    return svc
