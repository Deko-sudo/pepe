# Provider-specific embedded-chart delivery roadmap

> **Status:** REVISED — isolated TradingView-wrapper direction is owner-approved for architecture qualification; implementation remains separately gated. This document authorizes no runtime, CSP, CI, infrastructure, credential, ingestion, persistence, analytics, or Stage 9 change.
> **Baseline:** `main` at `4f83ce3e873410c156d0aa0480b84daff08d3177`, after merged PR #17 direct-iframe research.

## 1. Purpose and scope

This roadmap defines the ordered, separately reviewed work needed to deliver a provider-specific, display-only embedded chart. The direct-iframe-first path did not qualify a provider in C1. The owner subsequently approved an **isolated TradingView wrapper**: TradingView script runs only on a separate wrapper origin, while the Mini App embeds only that wrapper origin. See [isolated TradingView wrapper architecture](isolated-tradingview-wrapper-architecture.md).

The scope is BTC/USDT, ETH/USDT, and XAU/USD at `1m`, `5m`, `15m`, `1h`, `4h`, and `1d`, with a production activation only after all explicit gates below pass.

## 2. Current foundation

The merged foundation is server-authoritative and fail-closed:

- `MarketDataMode` supports `demo`, `embedded`, `live`, and `unavailable`.
- Embedded charts default to `EMBEDDED_CHART_ENABLED=false` and `EMBEDDED_CHART_PROVIDER=none`.
- The authenticated capability response is private/no-store; in embedded mode it keeps numeric quotes, server candles, quote cards, and embedded content unavailable.
- `GET /api/v1/market-data/embedded-chart-config` validates canonical slug/timeframe input, then returns versioned `409 market_data_unavailable` with `embedded_chart_provider_not_configured`.
- Root dashboard and `/markets` retain asset/timeframe selection in embedded mode, render a neutral provider-not-configured state, and do not request quotes/candles or fall back to DEMO.

W1–W5 are merged. W6 is delivered by the current PR, awaits exact-head contract and Docker CI evidence, then awaits owner merge approval; W7 is not started. W3 adds a fail-closed authenticated configuration contract for the isolated wrapper's 18 canonical local/test routes. W4 consumes only its validated server URL on `/markets`, with exact source/origin lifecycle checks and readiness-unknown semantics. Neither phase approves parent-CSP change, backend/provider network request, production activation, or Stage 9 change. Production remains blocked pending mandatory written TradingView confirmation and later W6–W7 gates.

## 3. Owner-approved direction

1. The direct-iframe C1 conclusion remains historical evidence; it selected no provider.
2. The owner-approved replacement direction is the isolated TradingView wrapper documented in PR W1; it is not a direct TradingView iframe or a top-level Pepe script integration.
3. Provider-specific work is delivered in focused PRs after each applicable gate.
4. Telegram Android and Telegram Desktop physical validation are mandatory.
5. Russia/DPR availability is recorded honestly but is not an initial planning blocker. Do not claim guaranteed availability, build jurisdiction-specific bypasses, send identity data, or treat VPN use as a technical/legal guarantee.
6. Production activation is intended only after technical, terms, security, device, rollback, infrastructure, and CI gates pass.

## 4. Non-goals

This roadmap does not authorize a provider choice, iframe/script/domain, credential, account, provider proxy, raw quote/candle extraction, scraping, iframe DOM access, `postMessage` market parsing, persistence, server analytics, synthetic fallback, Stage 9, or a change to CI in this PR.

## 5. Qualification gates

### Historical C1 direct-iframe gate

PR C1 used a bounded official-primary-source shortlist and required a direct HTTPS iframe, exact domains, exact instruments/intervals, public-display rights, attribution, cost/limitations, regional caveats, and Telegram WebView assumptions. It found no qualifying single provider. Those criteria and findings remain historical evidence in [the C1 record](direct-iframe-provider-selection.md); they are not a gate the approved wrapper path must satisfy.

### W1/W2 isolated-wrapper gate

The owner-approved wrapper path qualifies only when the evidence record includes current official TradingView script documentation and access date; terms/public-display assessment; attribution; canonical wrapper-route allowlisting; proposed symbol/interval mappings; instrument, venue, delay, and XAU semantics disclosures; exact observed wrapper subresource/frame origins; restrictive wrapper and parent CSP; validated sandbox; parent `referrerpolicy="no-referrer"`; fixed wrapper-owned lifecycle signals with documented readiness limits; regional caveats; and Telegram WebView validation assumptions. The official script may load only inside the separate wrapper origin, never Pepe's top-level document; no undocumented URL construction, raw-data extraction, proxy, resale, redistribution, client credential, or market-message parsing is permitted.

The wrapper gate does not silently substitute an instrument: BTC/USDT is not BTC/USD; ETH/USDT is not ETH/USD; XAU/USD is not futures, tokenized gold, XAU/USDT, another metal, or an undisclosed derivative. Crypto venue, XAU source semantics, and delay (`real-time`, `delayed`, or `unknown`) must be visible. Mandatory written TradingView confirmation remains a production gate under the architecture's current terms assessment.

## 6. Direct iframe technical requirements

The API provides only a server-authoritative public display configuration; the client renders an iframe from that allowlisted response. The client cannot provide arbitrary provider hosts, URLs, symbols, or intervals.

No provider script runs in Pepe's top-level document. Do not access iframe DOM/contentWindow, scrape, inspect screenshots, parse messages, intercept requests, copy market values, persist data, proxy provider traffic, or derive analytics. Iframe or fallback URLs must never include Telegram initData, session tokens, cookies, Authorization values, user identifiers, or deployment internals. External navigation is only user-initiated.

## 7. Instrument and timeframe requirements

Canonical values remain `btc-usdt`, `eth-usdt`, `xau-usd` and `1m`, `5m`, `15m`, `1h`, `4h`, `1d`. The provider adapter must reject an unknown slug/timeframe and all non-equivalent XAU mappings. Provider display mappings are versioned, reviewed data; they are not ingestion mappings or credentials.

## 8. Provider-specific API contract

Future work extends authenticated `GET /api/v1/market-data/embedded-chart-config` only after provider approval. It remains `Cache-Control: private, no-store`, validates canonical values before mapping, and returns no arbitrary URL/symbol, redirect, raw market data, credential, identity, or internal deployment detail.

A successful configuration contains only validated public fields:

- provider and configuration version;
- canonical slug and approved provider instrument identifier;
- canonical timeframe and provider interval;
- HTTPS iframe URL on an exact allowlisted origin;
- source and venue labels, market semantics, delay disclosure, and required attribution;
- an optional HTTPS fallback URL on a separately allowlisted origin, triggered only by the user.

Unavailable cases remain versioned `market_data_unavailable` and use: `embedded_chart_provider_not_configured`, `embedded_chart_disabled`, `embedded_chart_provider_unavailable`, `embedded_chart_instrument_unsupported`, `embedded_chart_timeframe_unsupported`, `embedded_chart_region_blocked`, and `embedded_chart_configuration_invalid`. `region_blocked` reports a result; it never suggests circumvention.

## 9. Frontend implementation

Both the root dashboard and `/markets` treat capabilities as authoritative. They retain asset/timeframe selectors; hide numeric cards and synthetic charts; issue no quote/candle request; and never show stale cached DEMO data in embedded mode.

Only after validated configuration may the direct iframe mount in a responsive Prime Unit-style container with accessible title, reduced-motion preservation, visible provider/source/venue/delay/attribution. Required states are capability loading/failure, configuration loading, provider disabled/not configured, unsupported instrument/timeframe, iframe loading/ready/timeout/blocked, provider unavailable, offline, region/provider denial, retryable network error, and permanent configuration error.

## 10. Security and privacy

All mappings, URLs, symbols, intervals, fallback destinations, and provider domains are server-controlled and come from explicit allowlists. No top-level provider script, raw extraction, persistence, analytics, provider proxy, iframe DOM access, or `postMessage` parsing is permitted. Iframe and fallback URLs carry no Pepe credential or Telegram data. No automatic external navigation is permitted.

## 11. CSP and domain allowlisting

A later security PR adds only owner-approved exact HTTPS iframe domains. It must use no wildcard `frame-src`, provider `script-src`, `unsafe-inline`, `unsafe-eval`, unnecessary `connect-src`, or broad `img-src`. The iframe must use `sandbox` and an explicit minimal `allow` list containing only provider-required permissions; top navigation, popups, and downloads remain prohibited unless separately owner-approved and tested. It uses a restrictive referrer policy and a separately allowlisted HTTPS fallback domain. Tests must prove CSP is emitted on SPA HTML responses despite Nginx header inheritance, and that an HTTPS iframe redirect to HTTP is blocked and surfaced unavailable.

## 12. Error handling and provider blocking

The health model is `configured`, `loading`, `iframe-loaded`, `ready`, `degraded`, `blocked`, `unavailable`, and `disabled`. A cross-origin `load` callback means only `iframe-loaded`; it is not chart readiness or provider health. `ready` requires an approved, origin-validated, non-market readiness signal from the selected provider; without one, provider health remains unknown. The component has a bounded load timeout, cancels it after the frame document loads, and retries by remounting the iframe with bounded user-triggered attempts—never a retry storm.

Handle browser offline state, DNS/network failure, and observable CSP blocking. Cross-origin browser isolation cannot always diagnose a precise cause; when it cannot, show generic provider unavailable. The whole Mini App, selector navigation, and auth remain usable. A fallback link is user-triggered only, uses `noopener,noreferrer`, contains no identity/session parameters, and never automatically redirects. Failure never switches to DEMO or fabricates values.

## 13. Telegram Android and Desktop verification

Before activation, record physical Telegram Android and Telegram Desktop results (optional iOS and standalone browsers add evidence but do not replace them). Verify auth, iframe load, scrolling/touch gestures, instrument/timeframe switches, dark-theme readability, attribution, safe fallback, timeout/retry/blocked/offline states, safe areas, back navigation, and no unexpected fullscreen/popup escape. Confirm no initData/session value reaches the provider. Regional results are recorded, not guaranteed; VPN use is neither a technical nor compliance conclusion.

## 14. Production activation

Source control remains disabled by default. After approval, deployment configuration may explicitly set `MARKET_DATA_MODE=embedded`, `EMBEDDED_CHART_ENABLED=true`, and `EMBEDDED_CHART_PROVIDER=<approved-provider>`. Startup validation fails closed for invalid/inconsistent settings; no secret is expected unless later approved separately.

Activation requires owner approval, verified public-display rights, official integration evidence, approved mappings/CSP, Android/Desktop smoke, outage handling, tested kill switch/rollback, and merged CI main-push hardening. There is no hidden selection or automatic DEMO fallback.

## 15. Kill switch and rollback

The immediate controls are `MARKET_DATA_MODE=unavailable` or `EMBEDDED_CHART_ENABLED=false`. A later implementation must define bounded capability polling or validated revalidation while an embedded chart is mounted, so active clients receive the kill switch, unmount the iframe, cease provider display requests, invalidate cached display configuration, and show a neutral unavailable state. Until that mechanism is implemented, rollback applies on the next Mini App load/reload and must not be described as immediate for already-open clients. Quote/candle requests remain disabled in either state.

Operational runbook: set the approved deployment control; verify capability and config endpoint fail closed; test a currently active client plus a fresh load/reload; verify iframe removal and no DEMO fallback; record recovery state; only re-enable after root cause and owner approval. Trigger shutdown for terms changes, blocking, security incidents, broken mappings/semantics, or widespread iframe failure.

## 16. Observability

Privacy-preserving events may cover configuration requested, mount attempted, load callback, timeout, retry, fallback click, offline, disabled, and generic unavailable. Metrics: iframe load success, timeout, retry success, blocked/unavailable, fallback use, and privacy-safe application-platform breakdown.

Never log iframe URL if it may be sensitive, initData, Authorization, sessions, cookies, user IDs, provider DOM/messages/content, or iframe market values.

## 17. CI hardening before production

A dedicated PR must correct CI before activation. It must run the same required jobs on `pull_request` and `push` to `main`, bind outcomes to the exact main SHA, avoid needless duplicate runs where practical, preserve branch protection, make post-merge failures visible, and document remediation.

Required jobs: Frontend, API, Quote Core, Migration, Bot, Worker, Worker integration, Stage 7 worker integration, and Docker. Acceptance evidence proves PR and main-push runs, exact SHA recording, visible failures, and successful exact-main reporting. This follows the observed absence of a recorded post-merge run for `83e3b02bb2f5321ed1d0188213401ee8c20a9e35`.

## 18. Documentation and disclosures

Publish the selected provider's dated official documentation/terms evidence, attribution, source/venue/instrument semantics, delay status, exact domain inventory, known limitations, regional caveat, and privacy disclosure. Do not promise regional availability or VPN effectiveness/compliance.

## 19. Planned pull requests

1. **PR C1 — Direct-iframe provider research:** **completed with no qualified single provider**; see [direct-iframe qualification results](direct-iframe-provider-selection.md). Its direct-iframe restriction is superseded by the later owner decision below, not rewritten.
2. **PR W1 — Wrapper architecture qualification:** merged.
3. **PR W2 — Static isolated wrapper foundation:** merged.
4. **PR W3 — Backend wrapper configuration contract:** merged.
5. **PR W4 — Mini App wrapper integration:** merged.
6. **PR W5 — CSP, blocking, and rollback hardening:** merged.
7. **PR W6 — CI main-push hardening:** delivered by the current PR and awaiting owner merge approval; see [W6 CI main-push security gates](tradingview-wrapper-w6-ci-main-gates.md). Must merge before production activation.
8. **PR W7 — Telegram validation and production activation:** production wrapper origin, DNS/TLS, Android/Desktop evidence, production config, kill-switch exercise, and launch checklist. Stop before merge.

Do not combine this sequence into an oversized PR unless the owner explicitly changes the plan.

## 20. Acceptance criteria

Before production: W1 is merged; the official TradingView script runs only inside the separate-origin wrapper and never in Pepe's top-level document; wrapper routes allowlist canonical slug/timeframe values with no arbitrary URL/symbol/interval; approved exact mappings and intervals; accepted XAU/USD semantics and visible disclosure; exact wrapper CSP and parent wrapper-only `frame-src`; validated minimal sandbox; parent iframe `referrerpolicy="no-referrer"` and equivalent restrictive parent response policy where appropriate; validated wrapper-owned lifecycle signaling with documented readiness limits; mandatory written TradingView confirmation for the intended public Mini App display; no Telegram/session/referrer data, extraction, persistence, or analytics; visible provider/source/venue/market semantics/delay/attribution; user-triggered fallback with `noopener,noreferrer`; working observable timeout/retry/unavailable behavior and honest `readiness-unknown` handling for unobservable nested content failures; successful active-client kill-switch propagation and rollback; Android/Desktop evidence; CI main-push hardening merged with green exact-main CI; and Stage 9 unchanged. The historical C1 conclusion remains: no qualified single direct-iframe provider was found.

## 21. Owner decisions still required

- exact production wrapper hostname, hosting platform, DNS procedure, and TLS management;
- final accepted OANDA XAU/USD semantics and visible disclosure;
- fallback-link policy, popup policy, and exact production wrapper/Pepe CSP domains;
- activation date and optional iOS smoke requirement.

No timeout or non-response is approval.

## 22. Stage 9 boundary

Stage 9 belongs to Zheka and is excluded. Embedded charts do not provide Pepe-owned machine-readable candles, therefore no indicator, analytics, report, alert, or inference may derive from iframe content. Stage 9 remains unavailable until a separately approved live data source and contract exist.
