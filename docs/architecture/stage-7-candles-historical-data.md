# Stage 7 — Candles and historical data

**Status:** completed and merged. This document records the implemented historical-candle contract and the Compose/CI operational boundary; it does not claim a concrete market-data provider or indicator implementation.

## Package and persistence boundary

`packages/quote-core` owns provider-neutral candle types, validation, UTC boundary helpers, timeframe durations, bootstrap-window calculations, and the deterministic fake provider. Both the API and worker install this package explicitly from the local repository (`packages/quote-core`) in CI and Docker images. It is not fetched from an external package index.

The `007` migration adds `market_candles`. A row is uniquely identified by `(instrument_id, timeframe, open_time)` and stores OHLC, optional base/quote volume and trade count, safe source/venue labels, and `received_at`. Values are UTC-aware; OHLC values are positive, `high` bounds all prices, `low` does not exceed open/close, and optional volume/trade-count values cannot be negative. The worker upserts this identity, so retries are idempotent.

## API contract

`GET /api/v1/market-data/instruments/{slug}/candles`

The endpoint requires the existing Stage 4 cookie session and returns `Cache-Control: private, no-store`. It accepts:

| Parameter | Required | Semantics |
|---|---:|---|
| `timeframe` | yes | One of `1m`, `5m`, `15m`, `1h`, `4h`, or `1d`. |
| `from` | no | RFC 3339 timezone-aware timestamp, normalized to UTC. |
| `to` | no | RFC 3339 timezone-aware timestamp, normalized to UTC. |
| `limit` | no | Number of rows, default `500`, minimum `1`, maximum `1000`. |

Rows are returned ascending by `open_time`. Each item contains `open_time`, `close_time`, string decimal `open`/`high`/`low`/`close`, optional string volumes and trade count, safe source/venue labels, and `received_at`. Provider credentials, provider symbols, raw payloads, URLs, mapping IDs, and failure diagnostics are not public fields.

The visible range is half-open: `open_time >= from` and `open_time < to`. When only `from` is provided, `to` is calculated as `from + timeframe * limit`; when only `to` is provided, `from` is calculated as `to - timeframe * limit`. With no range, the latest `limit` rows are selected, then returned in chronological order. When both bounds are present, `from` must precede `to` and their span may not exceed `timeframe * limit`; otherwise the endpoint returns `422`. Naive timestamps also return `422`. A missing or disabled instrument returns generic `404`; valid instruments with no persisted rows return `200` with an empty `items` array.

Only fully closed candles are requested by the worker. A candle closes exactly one timeframe after its aligned `open_time`; therefore an in-progress bar is neither persisted by the normal sync path nor returned as history.

## Timeframes, bootstrap, and incremental sync

All boundaries are elapsed UTC durations, not exchange-local calendar boundaries. The supported durations and first-sync lookback windows are:

| Timeframe | Duration | Bootstrap window |
|---|---:|---:|
| `1m` | 1 minute | 24 hours |
| `5m` | 5 minutes | 7 days |
| `15m` | 15 minutes | 30 days |
| `1h` | 1 hour | 180 days |
| `4h` | 4 hours | 365 days |
| `1d` | 1 day | 5 years |

On an empty instrument/timeframe, the worker fetches from the bootstrap-window start through the newest closed candle. On later runs, it starts two timeframe durations before the latest stored `open_time`, deliberately overlapping recent rows; the database identity/upsert makes that overlap safe. These bootstrap windows provide historical availability only. Indicator warm-up requirements must be specified and enforced by the future indicator consumer rather than inferred by this API.

## Queues, scheduler, and lease

Celery routing is explicit:

| Task | Queue | Default schedule |
|---|---|---:|
| `quote.refresh` | `quotes` | 60 seconds |
| `candles.sync` | `candles` | 300 seconds |

The Compose worker consumes `celery,quotes,candles`; the scheduler is a separate service and only dispatches scheduled tasks. Queue names and schedules can be changed with `QUOTE_QUEUE_NAME`, `CANDLE_QUEUE_NAME`, `QUOTE_SCHEDULER_INTERVAL_SECONDS`, and `CANDLE_SCHEDULER_INTERVAL_SECONDS`. The API does not enqueue a refresh or sync while serving a read.

Each candle sync target `(instrument UUID, timeframe)` takes a Redis `SET NX EX` lease at `pepe:candles:sync-lease:v1:<instrument-uuid>:<timeframe>`. Its default TTL is 300 seconds (`CANDLE_SYNC_LEASE_TTL_SECONDS`). The token is randomly owned and release uses compare-and-delete, so a worker cannot delete a lease it no longer owns. A held lease is a normal skipped sync; Redis lease unavailability is retryable. Provider, validation, and persistence failures are retryable and the Celery task uses exponential backoff with jitter. Leases are not renewed.

The deterministic fake candle source is enabled only when `CANDLE_FAKE_PROVIDER_ENABLED=true`; it is independently controlled from `QUOTE_FAKE_PROVIDER_ENABLED` and remains a development/Compose path, not a provider selection or production market-data claim.

## CI and integration boundary

Existing Stage 6 `Worker integration` remains intact and non-skipped: it provides PostgreSQL and Redis, applies migrations, and runs its environment-gated quote-refresh integration entrypoint. The non-skipped `Stage 7 worker integration` job independently provisions PostgreSQL and Redis, applies `alembic upgrade head`, installs local quote-core plus API/worker dependencies, provides `TEST_DATABASE_URL` and `TEST_REDIS_URL`, and runs `test_candle_sync_integration.py`. Those variables satisfy the test module's isolation guard, so the migration, PostgreSQL idempotency/rollback, Redis owner-safe lease, and concurrent-sync paths execute rather than skip.
