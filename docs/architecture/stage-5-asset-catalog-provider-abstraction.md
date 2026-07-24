# Stage 5 — Asset Catalog and Market Provider Abstraction

**Status:** APPROVED / IN PROGRESS

## Scope and exclusions

Stage 5 introduces the canonical, provider-independent asset catalog and its read-only API. It includes PostgreSQL persistence, deterministic metadata seeds, provider mapping persistence and typed provider contracts.

It explicitly excludes concrete providers, external HTTP requests, credentials, quotes, quote caches, candles, historical data, charts, analytics, liquidity filters, signals, frontend changes, worker tasks and scheduling. Stage 6 remains the boundary for current quote retrieval, retry/failover orchestration and cache policy.

## Canonical domain model

An instrument has an immutable UUID, stable lowercase kebab-case slug and canonical symbol. A canonical symbol is never a provider symbol. The model stores display metadata, enabled state and a positive metadata version.

Controlled asset classes:

- `crypto_spot`
- `metal_fx_spot`
- `equity_index`
- `currency_index`
- `government_yield`

Controlled market types:

- `spot`
- `reference_index`
- `yield_reference`

Calendar kinds are `always_open`, `provider_session`, `exchange` and `reference_data`. Calendars are identifiers and metadata only; Stage 5 has no market-calendar engine.

Spot crypto and metal/FX records require `spot` plus base/quote assets. Index classes require `reference_index`; government yields require `yield_reference`. This intentionally avoids crypto-specific assumptions for future index and yield definitions.

## Initial catalog

Revision `004` deterministically seeds exactly three enabled canonical instruments with explicit stable UUIDs:

| Slug | Symbol | Class | Calendar |
|---|---|---|---|
| `btc-usdt` | `BTC/USDT` | `crypto_spot` | `crypto-24x7` |
| `eth-usdt` | `ETH/USDT` | `crypto_spot` | `crypto-24x7` |
| `xau-usd` | `XAU/USD` | `metal_fx_spot` | `xau-usd-provider-session` |

No mappings, prices, volumes, liquidity metadata, S&P 500, NASDAQ, DXY or US10Y are seeded. Liquidity enforcement is deliberately deferred to future asset-class-specific policy. Future index/yield identities must not select a cash index, ETF, futures, CFD or yield proxy in Stage 5.

## PostgreSQL schema and migration

`asset_instruments` stores canonical metadata with named controlled-value, precision and metadata-version constraints, plus enabled catalog/filter indexes.

`provider_instrument_mappings` stores provider key, provider symbol, market, enabled state, positive priority and mapping version. It has surrogate UUID identifiers, restricted instrument deletion, business uniqueness for instrument/provider and provider symbol identity, and a partial unique enabled priority index. It contains no JSONB, URLs, raw payloads, credentials or API keys.

Alembic chain is `003 -> 004`. The migration is self-contained, upgrades with deterministic seeds, and downgrades by deleting dependent mappings, deleting seeded instruments and dropping mapping then catalog tables. CI verifies upgrade, exact seeds, downgrade to `003` and re-upgrade.

## Provider abstraction

`MarketDataProvider` is an async `Protocol`, not an inheritance framework. It declares identity, capabilities, health, supported mapping discovery and mapping availability only. Stage 5 provides no concrete adapter and therefore performs no network I/O.

Capabilities may declare future quote/candle support but do not expose quote or candle execution methods. Future adapters own provider-response/error normalization; future orchestration owns retry and failover. A future adapter operation must make one bounded request with an explicit timeout. Credentials may come only from environment/config, never mappings or client input.

Provider errors use a safe typed taxonomy: unmapped/unsupported, unavailable, authentication failure, rate limiting, invalid response, stale metadata, temporary transport failure and permanent configuration failure. They expose stable codes, retryability, safe public messages and bounded optional retry-after data. Raw errors, response bodies, headers, URL queries and credentials are neither persisted nor returned by the API.

## Mapping selection

Internal mapping selection considers enabled mappings only and orders by lowest priority followed by provider key. The database partial unique index prevents equal enabled priorities for an instrument. Missing mappings normalize to `InstrumentNotMapped`; an unmapped initial asset is a valid Stage-5 state. Mapping selection is not a public endpoint and clients cannot choose providers.

## API and authorization

- `GET /api/v1/assets`
- `GET /api/v1/assets/{slug}`

Both require the existing Stage-4 session dependency. They are GET-only and do not require CSRF. List pagination is keyset pagination by canonical slug (`limit` 1–100, default 50, optional `after`) with an optional controlled `asset_class` filter. Disabled and unknown details both produce the same 404. Responses expose canonical metadata only: no mappings, provider health/configuration, prices, volumes, candles or analytics.

## Security

The public surface is session-protected and read-only. All storage fields are bounded; SQLAlchemy queries are parameterized; ordering and provider selection are never client-controlled. Canonical IDs are immutable. There is no admin mutation API, SSRF surface, provider routing parameter, relationship serialization or Stage-6 network behavior.

## Testing and CI

Tests cover domain validation, provider contracts/error safety, model constraints, mapping selection and API authorization/response boundaries. Migration CI validates the exact seeded rows and empty mapping table after upgrade and re-upgrade. Compose smoke validates revision `004`, catalog tables and seeded asset count before API startup.

## Deferred work and Stage-6 boundary

Stage 6 may select a reviewed concrete provider, obtain credentials through configuration, implement bounded timeout-controlled adapter calls and define quote cache/staleness/failover behavior. It must not silently change canonical identity or the Stage-5 catalog API contract.
