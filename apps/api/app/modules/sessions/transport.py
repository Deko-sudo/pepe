from __future__ import annotations

from collections.abc import Mapping

SESSION_FALLBACK_HEADER = "X-Pepe-Session-Token"
SESSION_FALLBACK_REQUEST_HEADER = "X-Pepe-Session-Fallback"
SESSION_FALLBACK_REQUEST_VALUE = "telegram-desktop"


def session_fallback_requested(headers: Mapping[str, str]) -> bool:
    return (
        headers.get(SESSION_FALLBACK_REQUEST_HEADER, "").strip().casefold()
        == SESSION_FALLBACK_REQUEST_VALUE
    )
