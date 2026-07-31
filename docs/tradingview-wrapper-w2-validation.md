# W2 isolated TradingView wrapper validation

Date: 2026-07-31. Environment: local Chromium technical validation; wrapper `http://127.0.0.1:4173`, separate parent harness `http://127.0.0.1:4174`.

## Official mechanism

Official source: [Advanced Chart: Widget Code & Settings — TradingView](https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/) (accessed 2026-07-31). The page identifies the Advanced Chart as `type: iframe`, generates a `tradingview-widget-container`, visible attribution, configuration including `symbol`, `interval`, `theme`, `locale`, `timezone`, and `autosize`, and official script URL `https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js`.

Observed request: HTTP 200 with no redirect. SHA-256: `e49b74c1748b58e5d3bf0e42c1ce6d70f73dce57011a50d4fb1b62db450a8678`. This is observed change-detection evidence, not SRI or immutable pinning.

## Matrix

All 18 routes produced `wrapper-document-ready`, `provider-frame-created`, and `provider-frame-document-loaded`; every result remains `readiness-unknown`.

| Slug | Timeframes | TradingView mapping | Result |
|---|---|---|---|
| btc-usdt | 1m, 5m, 15m, 1h, 4h, 1d | BINANCE:BTCUSDT; 1, 5, 15, 60, 240, D | all six: frame document loaded; readiness-unknown |
| eth-usdt | 1m, 5m, 15m, 1h, 4h, 1d | BINANCE:ETHUSDT; 1, 5, 15, 60, 240, D | all six: frame document loaded; readiness-unknown |
| xau-usd | 1m, 5m, 15m, 1h, 4h, 1d | OANDA:XAUUSD; 1, 5, 15, 60, 240, D | all six: frame document loaded; readiness-unknown |

No price, candle, chart text, screenshot, cookie, identifier, or provider payload was captured. Frame load does not prove chart rendering, symbol acceptance, entitlement, regional availability, consent state, authentication state, or data availability.

## Observed origin inventory

Recorded structured inventory: `apps/tradingview-wrapper/provider/observed-origins.json`.

Observed HTTPS origins: `s3.tradingview.com` (official script), `s.tradingview.com` (outer provider frame), `s3-symbol-logo.tradingview.com`, `scanner-backend.tradingview.com`, `widget-sheriff.tradingview-widget.com`, `www.tradingview-widget.com`, and `www.tradingview.com`. No HTTP request or mixed content was observed. No wildcard host is approved. The wrapper CSP uses only the initial exact `s3.tradingview.com` script and `s.tradingview.com` frame boundary; nested provider subresources are documented for later W5 production CSP assessment, not approved here.

The official script inserts inline style in the wrapper document. A `style-src 'unsafe-inline'` exception is therefore present only in this local/test W2 CSP and is explicitly unresolved for production review.

## Harness, privacy, and layout

The parent harness used `referrerpolicy="no-referrer"`, `sandbox="allow-scripts allow-same-origin"`, and a synthetic `?test_private_marker=must_not_reach_wrapper`; the marker was absent from wrapper navigation and lifecycle payloads. The harness rejected forged wrong-origin, wrong-source, opaque-origin `null`, wrong-schema, unknown-event, and extra-field messages. It sends no commands. `allow-popups` was not granted; no top navigation permission is present. Narrow mobile (390×844) and desktop (1280×720) browser checks passed.

Script blocking produces the bounded observable script failure path; unobservable nested content failures remain `readiness-unknown` by design.

## Production blockers and dependencies

The build banner says: “Technical validation build. Public production display is not approved.” Terms remain unresolved: mandatory written TradingView confirmation for intended public display has not been obtained or accepted. Production wrapper hosting, DNS, TLS, exact production CSP/sandbox, XAU semantics owner acceptance, W3 backend contract, W4 Mini App integration, W5 rollback hardening, W6 CI main-push work, and W7 physical Telegram Android/Desktop validation are not implemented.
