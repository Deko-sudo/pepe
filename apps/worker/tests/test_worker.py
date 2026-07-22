from app.config import worker_settings
from app.tasks import heartbeat, test_task


def test_heartbeat_returns_ok() -> None:
    result = heartbeat()
    assert result["service"] == "pepe-worker"
    assert result["event"] == "heartbeat"
    assert result["status"] == "ok"


def test_test_task_returns_ok() -> None:
    result = test_task("hello")
    assert result["service"] == "pepe-worker"
    assert result["event"] == "test"
    assert result["status"] == "ok"
    assert result["value"] == "hello"


def test_redis_url_is_configured() -> None:
    assert worker_settings.redis_url is not None
    assert len(worker_settings.redis_url) > 0


def test_worker_settings_loads() -> None:
    assert worker_settings.log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def test_shutdown_handler_exists() -> None:
    from app.main import handle_signal

    assert callable(handle_signal)
