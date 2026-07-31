# Provider-specific embedded-chart delivery roadmap

> **Status:** PROPOSED — OWNER APPROVAL REQUIRED. This is documentation only. It selects no provider and authorizes no runtime, CSP, CI, infrastructure, credential, ingestion, persistence, analytics, or Stage 9 change.
> **Baseline:** `main` at `83e3b02bb2f5321ed1d0188213401ee8c20a9e35`, after the merged provider-neutral embedded-chart foundation.

## 1. Purpose and scope

This roadmap defines the ordered, separately reviewed work needed to deliver a provider-specific, display-only embedded chart after an owner selects a provider. It prevents the implementation PRs from re-deciding architecture: the initial direction is an **officially documented direct iframe** integration, not provider JavaScript in Pepe's top-level Mini App document.

The scope is BTC/USDT, ETH/USDT, and XAU/USD at `1m`, `5m`, `15m`, `1h`, `4h`, and `1d`, with a production activation only after all explicit gates below pass.

## 2. Current foundation

The merged foundation is server-authoritative and fail-closed:

- `MarketDataMode` supports `demo`, `embedded`, `live`, and `unavailable`.
- Embedded charts default to `EMBEDDED_CHART_ENABLED=false` and `EMBEDDED_CHART_PROVIDER=none`.
- The authenticated capability response is private/no-store; in embedded mode it keeps numeric quotes, server candles, quote cards, and embedded content unavailable.
- `GET /api/v1/market-data/embedded-chart-config` validates canonical slug/timeframe input, then returns versioned `409 market_data_unavailable` with `embedded_chart_provider_not_configured`.
- Root dashboard and `/markets` retain asset/timeframe selection in embedded mode, render a neutral provider-not-configured state, and do not request quotes/candles or fall back to DEMO.

## 3. Owner-approved direction

1. Prefer a provider with officially supported direct iframe delivery.
2. Do not select TradingView for the first implementation under this roadmap. If no acceptable direct-iframe provider qualifies, stop for owner re-approval.
3. TradingView remains only a future migration/fallback candidate, not a selected implementation.
4. Provider-specific work is delivered in separate PRs after roadmap approval.
5. Telegram Android and Telegram Desktop physical validation are mandatory.
6. Russia/DPR availability is recorded honestly but is not an initial planning blocker. Do not claim guaranteed availability, build jurisdiction-specific bypasses, send identity data, or treat VPN use as a technical/legal guarantee.
7. Production activation is intended only after technical, security, device, rollback, and CI gates pass.

## 4. Non-goals

This roadmap does not authorize a provider choice, iframe/script/domain, credential, account, provider proxy, raw quote/candle extraction, scraping, iframe DOM access, `postMessage` market parsing, persistence, server analytics, synthetic fallback, Stage 9, or a change to CI in this PR.

## 5. Provider qualification gate

PR C1 researches a bounded shortlist using current official primary sources only. A candidate qualifies only when the evidence record includes official documentation URL and access date, terms summary, attribution requirement, exact domains, instrument identifiers, interval mapping, cost, known limitations, regional caveats, and Telegram WebView compatibility assumptions.

Required qualifications:

- officially documented, stable direct iframe integration; no undocumented URL construction;
- no provider JavaScript in Pepe's top-level document;
- no account/API key if possible, free or very-low-cost initial use, and public display permitted with visible required attribution;
- no raw-data extraction, server proxy, resale, redistribution, or client-exposed credential;
- responsive dark-theme display and controls compatible with Pepe;
- exact support for the required instruments/timeframes, or explicit owner-approved unavailable behavior;
- official rights/terms suitable for a free informational Telegram Mini App.

The selection record must state why a split-provider design is or is not acceptable. It must not silently substitute an instrument: BTC/USDT is not BTC/USD; ETH/USDT is not ETH/USD; XAU/USD is not futures, tokenized gold, XAU/USDT, another metal, or an undisclosed derivative. Crypto venue, XAU source semantics, and delay (`real-time`, `delayed`, or `unknown`) must be visible.

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

1. **PR C1 — Provider research and selection:** **completed with no qualified single provider**; see [direct-iframe qualification results](direct-iframe-provider-selection.md). The current conclusion preserves the fail-closed foundation and requires a separate owner decision before renewed research. Stop before merge.
2. **PR C2 — Provider-specific backend contract:** enum/validation, allowlisted mappings, successful config response, tests; no frontend iframe. Stop before merge.
3. **PR C3 — Frontend direct iframe integration:** dashboard and `/markets`, lifecycle/attribution/timeout/retry/fallback, no quote/candle requests. Stop before merge.
4. **PR C4 — CSP and provider-blocking hardening:** exact CSP/domain allowlist, SPA-header verification, outage/security tests. Stop before merge.
5. **PR C5 — CI main-push hardening:** push-to-main workflow, exact-SHA proof, remediation documentation. Stop before merge.
6. **PR C6 — Telegram validation and production activation:** Android/Desktop evidence, kill-switch/rollback exercise, production configuration, launch checklist. Stop before merge.

Do not combine this sequence into an oversized PR unless the owner explicitly changes the plan.

## 20. Acceptance criteria

Before production: an owner-approved direct-iframe provider with official integration/public-display evidence; approved exact mappings and intervals or approved unavailable handling; no top-level provider script/arbitrary URL/symbol; no Telegram/session data, extraction, persistence, or analytics; visible provider/source/venue/market semantics/delay/attribution; user-triggered fallback with `noopener,noreferrer`; working timeout/retry/blocked/outage states; successful kill switch/rollback; Android/Desktop evidence; CI main-push hardening merged with green exact-main CI; and Stage 9 unchanged.

## 21. Owner decisions still required

- final provider and exact instrument/interval identifiers;
- whether split providers are acceptable;
- fallback-link policy and exact production CSP/fallback domains;
- activation date and whether TradingView remains documented as a future alternative;
- optional iOS smoke requirement.

No timeout or non-response is approval.

## 22. Stage 9 boundary

Stage 9 belongs to Zheka and is excluded. Embedded charts do not provide Pepe-owned machine-readable candles, therefore no indicator, analytics, report, alert, or inference may derive from iframe content. Stage 9 remains unavailable until a separately approved live data source and contract exist.
