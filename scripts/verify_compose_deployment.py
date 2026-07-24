#!/usr/bin/env python3
"""Validate the Compose migration and session-settings deployment contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ENVIRONMENT_KEYS = (
    "APP_ENV",
    "CORS_ALLOWED_ORIGINS",
    "DATABASE_URL",
    "SESSION_COOKIE_NAME",
    "SESSION_ABSOLUTE_TTL_SECONDS",
    "SESSION_IDLE_TTL_SECONDS",
    "SESSION_MAX_ACTIVE",
    "SESSION_COOKIE_SECURE",
    "SESSION_ALLOWED_ORIGINS",
)
MIGRATE_ENVIRONMENT_KEYS = ("DATABASE_URL",)
CUSTOM_ENVIRONMENT = {
    "APP_ENV": "production",
    "CORS_ALLOWED_ORIGINS": "https://mini.example.com",
    "DATABASE_URL": "postgresql+asyncpg://custom:custom@postgres:5432/custom",
    "SESSION_COOKIE_NAME": "custom_session",
    "SESSION_ABSOLUTE_TTL_SECONDS": "2592000",
    "SESSION_IDLE_TTL_SECONDS": "604800",
    "SESSION_MAX_ACTIVE": "5",
    "SESSION_COOKIE_SECURE": "true",
    "SESSION_ALLOWED_ORIGINS": "https://mini.example.com",
}


def render_compose(environment: dict[str, str] | None = None) -> dict[str, Any]:
    command_environment = os.environ.copy()
    if environment is not None:
        command_environment.update(environment)
    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        check=True,
        cwd=ROOT,
        env=command_environment,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def environment_mapping(service: dict[str, Any]) -> dict[str, str]:
    environment = service.get("environment", {})
    if not isinstance(environment, dict):
        raise AssertionError("Compose service environment must render as an object")
    return {key: str(value) for key, value in environment.items()}


def assert_migration_contract(rendered: dict[str, Any], expected_environment: dict[str, str]) -> None:
    services = rendered.get("services", {})
    if not isinstance(services, dict):
        raise AssertionError("Compose config must include services")

    migrate = services.get("migrate")
    api = services.get("api")
    if not isinstance(migrate, dict) or not isinstance(api, dict):
        raise AssertionError("Compose config must define api and migrate services")

    command = migrate.get("command")
    if command != ["alembic", "upgrade", "head"]:
        raise AssertionError("migrate command must be exactly ['alembic', 'upgrade', 'head']")
    if migrate.get("restart") != "no":
        raise AssertionError("migrate must be a one-shot service with restart: no")
    if migrate.get("ports"):
        raise AssertionError("migrate must not publish ports")

    migrate_dependencies = migrate.get("depends_on", {})
    if migrate_dependencies.get("postgres", {}).get("condition") != "service_healthy":
        raise AssertionError("migrate must wait for healthy postgres")

    api_dependencies = api.get("depends_on", {})
    if api_dependencies.get("migrate", {}).get("condition") != "service_completed_successfully":
        raise AssertionError("api must wait for successful migrate completion")
    if api_dependencies.get("redis", {}).get("condition") != "service_healthy":
        raise AssertionError("api must preserve the healthy redis dependency")

    api_environment = environment_mapping(api)
    migrate_environment = environment_mapping(migrate)
    if set(migrate_environment) != set(MIGRATE_ENVIRONMENT_KEYS):
        raise AssertionError("migrate must receive only DATABASE_URL")
    for key in API_ENVIRONMENT_KEYS:
        if api_environment.get(key) != expected_environment[key]:
            raise AssertionError(f"rendered {key} did not match the expected value")
    for key in MIGRATE_ENVIRONMENT_KEYS:
        if migrate_environment.get(key) != expected_environment[key]:
            raise AssertionError(f"rendered migrate {key} did not match the expected value")


def main() -> int:
    defaults = {
        "APP_ENV": "development",
        "CORS_ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:4000,http://localhost:8080",
        "DATABASE_URL": "postgresql+asyncpg://pepe:change_me@postgres:5432/pepe",
        "SESSION_COOKIE_NAME": "pepe_session",
        "SESSION_ABSOLUTE_TTL_SECONDS": "2592000",
        "SESSION_IDLE_TTL_SECONDS": "604800",
        "SESSION_MAX_ACTIVE": "5",
        "SESSION_COOKIE_SECURE": "false",
        "SESSION_ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:4000,http://localhost:8080",
    }
    assert_migration_contract(render_compose(defaults), defaults)
    assert_migration_contract(render_compose(CUSTOM_ENVIRONMENT), CUSTOM_ENVIRONMENT)
    print("COMPOSE_DEPLOYMENT_CONTRACT_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"COMPOSE_DEPLOYMENT_CONTRACT_FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
