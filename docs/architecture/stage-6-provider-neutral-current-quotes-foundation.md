# Stage 6 PR 1 — Provider-neutral Current Quotes Foundation

**Status:** COMPLETED AND MERGED — provider-neutral foundation.

## Approved boundary

This slice implements D3–D7 and D10 plus the provider-neutral directions of D8, D9, D11 and D12. D1 and D2 remain deferred. It does not select, configure, contact or attribute a real market-data provider.

Stage 6 is split deliberately:

1. This PR provides the durable/current-quote foundation, deterministic fake provider, internal scheduling and safe read API.
2. A later explicitly approved PR may add a reviewed concrete provider, mappings, credentials, commercial rights and final production values.

## Dependency direction

`packages/quote-core` is an installable Python package. API and worker import it; quote-core imports neither application. It owns normalized quote semantics, Decimal validation, freshness calculation, recency comparison, redaction-safe public provenance types, the quote Provider Protocol and deterministic fake provider.

Quote-core contains no FastAPI routing, Stage-4 session code, Celery bootstrap, SQLAlchemy lifecycle, environment loading, HTTP client, credential or Telegram code.

## Domain and safety

Quotes use `Decimal`, UTC-aware timestamps and explicit `MarketType`, `PriceType`, `MarketStatus`, `DataStatus` and `DelayClass` enums. Price type and market type are independent. Public decimals serialize as ordinary strings. NaN, infinity, invalid bid/ask, invalid low/high, negative volumes and invalid timestamps are rejected.

The deterministic fake provider supports only canonical test scenarios for `btc-usdt`, `eth-usdt` and `xau-usd`. It does not issue external requests. Fake mode is explicit in development/Compose and rejected by API production settings.

## Persistence, cache and refresh flow

Alembic `005` adds `latest_market_quotes`; additive Alembic `006` persists the provider provenance snapshot alongside each value. The table stores one latest accepted value per canonical instrument, using the instrument UUID as primary key and restricted foreign keys to catalog and mapping records. It is not a tick store and has no append-only history. The worker's atomic upsert rejects older observations and resolves equal timestamps deterministically through the provider event identifier.

Redis is a best-effort versioned latest-value cache under `pepe:quotes:v1:<instrument-uuid>`. Cache reads are strict and corrupted/unknown payloads are misses. Redis failure falls back to PostgreSQL; it never removes the durable quote. The PostgreSQL fallback reconstructs the same v1 nested provenance object from the persisted source label, nullable venue label, market type, price type and delay class. Cache keys never contain user input, provider symbols or credentials.

Celery uses the dedicated `quotes` queue and a separate scheduler service. Scheduler dispatches `quote.refresh`; the worker only runs the deterministic fake path when explicitly enabled. It seeds only non-production synthetic mappings at refresh time, then writes normalized values to durable storage. No user-facing request enqueues or forces refresh.

## Worker integration CI

The `Worker integration` GitHub Actions job provisions isolated PostgreSQL 16 and Redis 7
services. It installs the API, worker and quote-core packages, applies `alembic upgrade head`
against the service PostgreSQL database, and runs
`apps/worker/tests/test_quote_refresh_integration.py -q`. The job supplies both
`TEST_DATABASE_URL` and `TEST_REDIS_URL`, so the integration module's environment gate is
satisfied and its Redis lease, PostgreSQL persistence/rollback, and concurrent-refresh paths
are executed instead of skipped. The job has read-only repository permissions and checkout
does not persist credentials.

## API and freshness

- `GET /api/v1/assets/{slug}/quote`
- `GET /api/v1/assets/quotes?slug=btc-usdt&slug=eth-usdt`

Both reuse the Stage-4 session dependency. They return `Cache-Control: private, no-store`. A fresh or stale durable value returns `200` with explicit `data_status` and `age_seconds`. For the single-asset endpoint, a hard-expired or absent value returns generic `503`; batch requests return `200` with unavailable slugs. Unknown and disabled records are not disclosed through provider diagnostics. Batch ordering is canonical slug order and duplicate requested slugs are deduplicated.

Public provenance exposes only safe labels, market type, price type and delay class. Provider key, mapping ID/version, provider symbol, URL, raw payload, failure diagnostics and credentials never appear in responses.

Freshness is configured by asset class. Defaults are deterministic development/test values only, not final production thresholds. `market_status=closed` remains independent from freshness; this PR makes no local assertion about XAU/USD market hours.

## Health, security and deferred work

API liveness remains `/api/v1/health`; readiness checks PostgreSQL and Redis. Provider failure does not make API liveness fail. Worker/scheduler are deployed separately in Compose.

No concrete provider, HTTP adapter, market-data network call, credential, production mapping, vendor attribution, WebSocket ingestion, candles, history, analytics, notification, real market UI or Stage 7 work is included.

Roadmap state: Stages 1–8 are complete and merged. Official completion is `8/12 = 67%`.
