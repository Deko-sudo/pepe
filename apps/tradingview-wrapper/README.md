# Isolated TradingView wrapper — W2

## Status

Technical-validation foundation only. W3's separate backend contract may return this wrapper's canonical local/test routes, but it does not approve production public display, hosting, DNS, TLS, Mini App integration, provider activation, or Stage 9.

## Isolation

`Pepe origin -> wrapper origin -> TradingView-controlled origins`.

Only this wrapper loads `https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js`. The Mini App is unchanged. The official script creates its own nested provider iframe; this project never constructs a provider iframe URL, reads its DOM, parses its messages, extracts market content, or accepts parent commands.

## Local commands

```text
make tradingview-wrapper-lint
make tradingview-wrapper-typecheck
make tradingview-wrapper-test
make tradingview-wrapper-build
make tradingview-wrapper-e2e
make tradingview-wrapper-provider-check
```

The local wrapper/test origin is `http://127.0.0.1:4173`; the test-only parent harness is `http://127.0.0.1:4174`. The Docker image serves only built static files on port 8080 as a non-root Nginx image. It accepts no environment secrets and does not contact TradingView at startup.

## Route contract

Only `/chart/{btc-usdt|eth-usdt|xau-usd}/{1m|5m|15m|1h|4h|1d}` is generated. Query strings and fragments cause `wrapper-configuration-invalid` and prevent the provider script from loading. Other routes return a neutral local error document.

Mappings are immutable: BTC/USDT → `BINANCE:BTCUSDT`; ETH/USDT → `BINANCE:ETHUSDT`; XAU/USD → `OANDA:XAUUSD`. Intervals are `1m→1`, `5m→5`, `15m→15`, `1h→60`, `4h→240`, `1d→D`. XAU/USD is explicitly displayed as an OANDA broker/reference-style quote, not exchange-traded spot; final acceptance is still an owner production gate.

## Lifecycle protocol

The wrapper sends only `{ type: "pepe.tradingview-wrapper.lifecycle", version: 1, event }`, where `event` is one of `wrapper-document-ready`, `provider-script-load-failed`, `provider-frame-created`, `provider-frame-document-loaded`, `provider-frame-timeout`, or `wrapper-configuration-invalid`.

The harness accepts a message only when both exact wrapper `event.origin` and expected iframe `event.source` match. It rejects `null`, unknown events, wrong schema/version, wrong source, wrong origin, and extra fields. No provider-ready event exists: frame-document-loaded means only the nested frame fired `load`; readiness remains `readiness-unknown`.

## Security model

The harness embeds with `sandbox="allow-scripts allow-same-origin"` and `referrerpolicy="no-referrer"`; it sends no commands. `allow-popups` is intentionally absent. The wrapper emits CSP, nosniff, no-referrer, restrictive Permissions-Policy, noindex and CORP headers. Its observed test CSP is exact-host HTTPS-only for TradingView. The official script requires inline style insertion, so the local W2 wrapper records the narrow `style-src 'unsafe-inline'` exception; final production CSP remains unresolved and needs a W5 review.

No storage, cookie write, auth, Telegram data, analytics SDK, API key, credentials, or parent private data exists in this wrapper.

## Provider change detection

`provider/tradingview-script.json` records an observed hash, not an immutable pin. `make tradingview-wrapper-provider-check` retrieves only the exact official script URL, rejects HTTP redirects, compares SHA-256, and fails on a change without modifying metadata. A change requires explicit review and complete origin/subresource revalidation before any later approval.

## Remaining blockers

Written TradingView confirmation for intended public display, production origin/hosting/DNS/TLS, accepted production CSP/sandbox, W3–W7, physical Telegram testing, XAU owner acceptance, and CI/main-push hardening remain mandatory. See `docs/tradingview-wrapper-w2-validation.md`.
