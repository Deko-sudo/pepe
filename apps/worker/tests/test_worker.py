from unittest.mock import AsyncMock

import asyncpg
import pytest
from pydantic import ValidationError
from redis.exceptions import RedisError

from app import candle_sync, quote_refresh
from app.celery_app import celery_app
from app.config import WorkerSettings, worker_settings
from app.tasks import heartbeat, refresh_quotes, run_test_task, sync_candles


def test_heartbeat_returns_ok() -> None:
    result = heartbeat()
    assert result["service"] == "pepe-worker"
    assert result["event"] == "heartbeat"
    assert result["status"] == "ok"


def test_test_task_returns_ok() -> None:
    result = run_test_task("hello")
    assert result["service"] == "pepe-worker"
    assert result["event"] == "test"
    assert result["status"] == "ok"
    assert result["value"] == "hello"


def test_redis_url_is_configured() -> None:
    assert worker_settings.redis_url is not None
    assert len(worker_settings.redis_url) > 0


def test_worker_settings_loads() -> None:
    assert worker_settings.log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def test_scheduler_interval_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        WorkerSettings(quote_scheduler_interval_seconds=0)


def test_quote_refresh_retries_transient_datastore_failures_with_bounded_backoff() -> None:
    task = refresh_quotes._get_current_object()
    assert task.autoretry_for == (OSError, asyncpg.PostgresError, RedisError)
    assert task.retry_backoff is True
    assert task.retry_backoff_max == 600


def test_candle_task_uses_dedicated_queue_schedule_and_transient_retries() -> None:
    task = sync_candles._get_current_object()
    assert celery_app.conf.task_routes["candles.sync"] == {
        "queue": worker_settings.candle_queue_name,
    }
    schedule = celery_app.conf.beat_schedule["sync-fake-historical-candles"]
    assert schedule["task"] == "candles.sync"
    assert schedule["schedule"] == worker_settings.candle_scheduler_interval_seconds
    assert task.autoretry_for == (OSError, asyncpg.PostgresError, RedisError)
    assert task.retry_backoff_max == 600


@pytest.mark.asyncio
async def test_fake_candle_runner_has_a_dedicated_enablement_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync = AsyncMock(return_value={"status": "ok", "synced": 0, "skipped": 0})
    monkeypatch.setattr("app.candle_sync.worker_settings.candle_fake_provider_enabled", True)
    monkeypatch.setattr("app.candle_sync.sync_candles", sync)

    result = await candle_sync.sync_fake_candles()

    assert result == {"status": "ok", "synced": 0, "skipped": 0}
    await_args = sync.await_args
    assert await_args is not None
    provider = await_args.args[0]
    assert provider.__class__.__name__ == "FakeHistoricalCandleProvider"
    assert "now" in await_args.kwargs


@pytest.mark.asyncio
async def test_fake_candle_runner_does_not_connect_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect = AsyncMock()
    monkeypatch.setattr("app.candle_sync.worker_settings.candle_fake_provider_enabled", False)
    monkeypatch.setattr("app.candle_sync.asyncpg.connect", connect)

    assert await candle_sync.sync_fake_candles() == {"status": "disabled", "synced": 0}
    connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_closes_postgres_when_redis_client_setup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = AsyncMock()
    connect = AsyncMock(return_value=connection)

    def redis_from_url(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("app.quote_refresh.worker_settings.quote_fake_provider_enabled", True)
    monkeypatch.setattr("app.quote_refresh.asyncpg.connect", connect)
    monkeypatch.setattr("app.quote_refresh.redis_asyncio.from_url", redis_from_url)

    with pytest.raises(RuntimeError, match="redis unavailable"):
        await quote_refresh.refresh_fake_quotes()

    connect.assert_awaited_once_with(
        worker_settings.database_url.replace("+asyncpg", ""),
        timeout=10,
        command_timeout=10,
    )
    connection.close.assert_awaited_once()


def test_shutdown_handler_exists() -> None:
    from app.main import handle_signal

    assert callable(handle_signal)
