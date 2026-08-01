# W4 Mini App isolated-wrapper integration

## Scope

W4 integrates the authenticated W3 embedded-chart configuration contract into the Mini App `/markets` surface. W1, W2, and W3 are merged. W4 is delivered by this PR and awaits owner merge; W5, W6, and W7 have not started.

## Boundary

The Mini App first reads authenticated market-data capabilities. It requests configuration only when embedded charts are available with provider `tradingview_isolated_wrapper` and contract version `1`. The W3 API remains authoritative: the browser validates the entire response and uses the supplied `wrapper_url` unchanged. It rejects unsupported contracts, malformed URLs, credentials, queries, fragments, path/origin mismatches, TradingView hosts, and same-origin configurations.

The iframe is separate-origin, uses only `sandbox="allow-scripts allow-same-origin"` and `referrerpolicy="no-referrer"`, and has no permissions-policy `allow` attribute or `srcdoc`. No frontend wrapper-origin variable, direct provider URL, top-level provider script, wrapper fetch, quote/candle request, or content extraction is introduced.

## Lifecycle

The Mini App consumes only W2's closed `{ type, version, event }` lifecycle payload: `pepe.tradingview-wrapper.lifecycle`, version `1`, and one of the six W2 allowlisted events. It requires exact wrapper origin, exact active iframe source identity, and rejects `null` origins and all other payloads. It sends no messages. Iframe and document-load signals are not provider readiness; nested frame document load is displayed as readiness unknown. Observable wrapper failure and timeout are neutral unavailable states. Listeners are scoped to the active iframe and removed on replacement/unmount.

## Production boundary

The W2 deterministic separate-origin wrapper fixture remains local and contains no TradingView dependency; W4 does not add a Mini App browser fixture or a live third-party CI dependency. W4 does not activate a provider, change parent CSP, add hosting/DNS/TLS, or implement W5 CSP/kill-switch/rollback controls. W6 workflow changes, W7 production gates, and Stage 9 remain out of scope. Written TradingView confirmation remains mandatory before production activation.
