# TradingView wrapper W3 backend contract

## Status

W1, W2, and W3 are merged. W4 consumes this contract through the Mini App `/markets` surface and is delivered by its current PR awaiting owner merge approval. W5–W7 are not started. This contract does not approve TradingView public display, production activation, hosting, DNS, TLS, CSP changes, or the mandatory written TradingView confirmation.

## Configuration and fail-closed policy

`EMBEDDED_CHART_ENABLED=false`, `EMBEDDED_CHART_PROVIDER=none`, and an empty `EMBEDDED_CHART_WRAPPER_ORIGIN` are the safe defaults. The only W3 provider values are `none` and `tradingview_isolated_wrapper`.

The enabled provider requires `MARKET_DATA_MODE=embedded`, a non-empty wrapper origin, and a development/test environment. Production rejects the provider without a bypass. Disabled/provider-none with an empty origin succeeds; every contradictory combination fails settings validation.

The origin is parsed without DNS or HTTP access. It must be a bare HTTP(S) origin with no credentials, path (other than `/`), query, fragment, wildcard, whitespace, control character, backslash, or percent encoding. Scheme and DNS host are lowercased, one trailing DNS root dot is removed, and default ports are removed. HTTP is permitted only for `http://127.0.0.1` in development/test. HTTPS accepts only validated ASCII DNS names: all IPv4/IPv6 literals and browser-normalized numeric IPv4 spellings are rejected.

## Authenticated configuration API

`GET /api/v1/market-data/embedded-chart-config` remains authenticated and returns `Cache-Control: private, no-store`. Its only successful W3 response is version `1` with mode `embedded`, provider `tradingview_isolated_wrapper`, canonical asset/timeframe, `wrapper_origin`, `wrapper_path`, and `wrapper_url`.

The exact routes are the cartesian product of `btc-usdt`, `eth-usdt`, `xau-usd` and `1m`, `5m`, `15m`, `1h`, `4h`, `1d`: exactly 18 `/chart/<asset>/<timeframe>` paths. The API generates the path and URL; it never accepts arbitrary URL/path/symbol/interval/query input and never exposes TradingView provider symbols.

Capabilities remain authenticated and private/no-store. Valid local/test configuration reports the provider and config version `1`; disabled embedded mode retains the established unavailable contract.

## Boundaries

W3 makes no backend wrapper fetch, DNS lookup, TradingView fetch, proxy, market-data ingestion, quote/candle change, parent CSP change, wrapper-runtime change, analytics, user/session/Telegram forwarding, or Stage 9 change. W4 consumes only a validated server URL; it performs no wrapper/provider fetch, does not inspect iframe DOM, and remains offline relative to TradingView in CI. W5 owns runtime kill-switch/rollback integration; W6 and W7 retain their main-push and production gates.
