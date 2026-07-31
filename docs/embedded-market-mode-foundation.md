# Embedded market-mode safety foundation (PR A)

PR A introduces the server-authoritative `MARKET_DATA_MODE` contract. Valid values are `demo`, `embedded`, `live`, and `unavailable`; unknown values fail configuration validation.

`demo` is the only mode that can expose the existing synthetic quote and candle paths. It is prohibited in production. Synthetic quote and candle providers are prohibited in every non-demo mode, including in direct worker entry points and the scheduler. Embedded, live-without-provider, and unavailable modes return no machine-readable market values.

Authenticated clients obtain `GET /api/v1/market-data/capabilities`, version `v1`, with `Cache-Control: private, no-store`. The response contains public mode/capability state only; it contains no credentials, deployment configuration, session identifiers, or user data. Missing or invalid capability responses are handled as unavailable by the Mini App.

When machine-readable quotes or candles are unavailable, protected endpoints return HTTP `409` with the versioned `market_data_unavailable` contract and `Cache-Control: private, no-store`. They do not return empty success responses, stale DEMO values, or fabricated data.

PR A does not select a provider, add an iframe, add third-party scripts, ingest market data, or implement Stage 9. External embedded-chart integration is deferred to PR B. Roll back safely by setting `MARKET_DATA_MODE=unavailable` with fake providers disabled.
