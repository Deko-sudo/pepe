from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from pepe_quote_core import (
    DataStatus,
    DelayClass,
    FakeQuoteProvider,
    MarketStatus,
    MarketType,
    PriceType,
    QuoteRequest,
)


async def test_fake_provider_returns_a_valid_deterministic_quote() -> None:
    instrument_id = uuid.UUID("a6d8c260-3f98-4d19-9e87-8dd33413b401")
    now = datetime(2026, 7, 25, tzinfo=UTC)
    provider = FakeQuoteProvider(clock=lambda: now)

    quote = await provider.fetch_quotes(
        [
            QuoteRequest(
                instrument_id=instrument_id,
                instrument_slug="btc-usdt",
                provider_key="fake",
                provider_mapping_id=uuid.UUID("4e204e08-1f55-4dc7-a8d2-a4f36b29ea49"),
                provider_instrument_id="test-btc-usdt",
                mapping_version=1,
            ),
        ],
    )

    assert len(quote) == 1
    result = quote[0]
    assert result.price == Decimal("60000.00")
    assert result.instrument_id == instrument_id
    assert result.observed_at == now
    assert result.provider_timestamp == now
    assert result.market_type is MarketType.SPOT
    assert result.price_type is PriceType.LAST_TRADE
    assert result.market_status is MarketStatus.OPEN
    assert result.data_status is DataStatus.FRESH
    assert result.delay_class is DelayClass.REALTIME
    assert result.source_label == "Synthetic test source"
    assert result.provenance.source_label == "Synthetic test source"
