from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pepe_quote_core import CandleTimeframe
from sqlalchemy import Select

from app.api.dependencies.session import require_current_session
from app.db.models.market_candle import MarketCandle
from app.main import app
from app.modules.market_data.candles import HistoricalCandleService
from app.schemas.candles import CandleResponse, CandlesResponse

_INSTRUMENT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_OPEN_TIME = datetime(2026, 7, 26, 12, tzinfo=UTC)


def _candle(open_time: datetime = _OPEN_TIME) -> SimpleNamespace:
    return SimpleNamespace(
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=Decimal("100.00"),
        high=Decimal("101.00"),
        low=Decimal("99.00"),
        close=Decimal("100.50"),
        base_volume=Decimal("12.5"),
        quote_volume=None,
        trade_count=4,
        source_label="test-source",
        venue_label=None,
        received_at=open_time + timedelta(minutes=1),
    )


class _ScalarRows:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self._rows


class _Database:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.statements: list[object] = []
        self._rows = rows

    async def scalar(self, statement: object) -> SimpleNamespace:
        self.statements.append(statement)
        return SimpleNamespace(id=_INSTRUMENT_ID)

    async def scalars(self, statement: object) -> _ScalarRows:
        self.statements.append(statement)
        return _ScalarRows(self._rows)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async def authenticated() -> SimpleNamespace:
        return SimpleNamespace()

    app.dependency_overrides[require_current_session] = authenticated
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_latest_candles_selects_from_the_limited_subquery_without_a_self_join() -> None:
    db = _Database([_candle()])

    result = await HistoricalCandleService().resolve(
        cast(Any, db),
        slug="btc-usdt",
        timeframe=CandleTimeframe.ONE_MINUTE,
        from_time=None,
        to_time=None,
        limit=2,
    )

    statement = cast(Select[Any], db.statements[1])
    sql = str(statement)
    assert "JOIN" not in sql
    assert "ORDER BY market_candles.open_time DESC" in sql
    assert "ORDER BY market_candles.open_time ASC" not in sql
    assert "ORDER BY anon_1.open_time ASC" in sql
    assert sql.count("LIMIT") == 1
    assert result is not None
    assert result.items[0].open == "100.00"


def test_candle_response_preserves_zero_prices_without_using_a_fallback() -> None:
    response = CandleResponse.from_values(
        open_time=_OPEN_TIME,
        close_time=_OPEN_TIME + timedelta(minutes=1),
        open_price=Decimal("0"),
        high=Decimal("0"),
        low=Decimal("0"),
        close=Decimal("0"),
        base_volume=None,
        quote_volume=None,
        trade_count=None,
        source_label="test-source",
        venue_label=None,
        received_at=_OPEN_TIME,
    )

    assert response.model_dump(mode="json")["open"] == "0"


@pytest.mark.asyncio
async def test_candles_endpoint_returns_serialized_history_and_no_store_header(
    client: AsyncClient,
) -> None:
    result = CandlesResponse(
        timeframe=CandleTimeframe.ONE_MINUTE,
        items=[
            CandleResponse(
                open_time=_OPEN_TIME,
                close_time=_OPEN_TIME + timedelta(minutes=1),
                open="100",
                high="101",
                low="99",
                close="100.5",
                base_volume="12.5",
                quote_volume=None,
                trade_count=4,
                source_label="test-source",
                venue_label=None,
                received_at=_OPEN_TIME + timedelta(minutes=1),
            ),
        ],
    )
    with patch(
        "app.api.v1.candles.HistoricalCandleService.resolve",
        AsyncMock(return_value=result),
    ):
        response = await client.get("/api/v1/market-data/instruments/btc-usdt/candles?timeframe=1m")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["items"][0]["open"] == "100"


def test_market_candle_unique_constraint_is_the_only_identity_index() -> None:
    assert not cast(Any, MarketCandle.__table__).indexes
