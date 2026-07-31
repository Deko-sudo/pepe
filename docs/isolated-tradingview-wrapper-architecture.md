# Isolated TradingView wrapper architecture (PR W1)

> **Decision status:** ARCHITECTURE MERGED. W2 static technical-validation evidence is merged. W3's backend-only configuration contract is delivered separately and awaits owner merge approval; neither approves production integration, contractual use, hosting, CSP, or provider activation.
> **Research date:** 2026-07-31. Official public sources below were accessed on that date from an unauthenticated environment.

## 1. Decision status

**Owner decision:** use an isolated TradingView-wrapper architecture as the next delivery direction. The architecture is technically viable because TradingView's current official Advanced Chart documentation supplies generated script-based widget markup, including a fixed official external script source and configuration object.

**Production status:** blocked pending the terms/public-display, hosting/DNS/TLS, exact domain-inventory, and physical Telegram validation gates in this document. Owner authorization is not evidence of TradingView contractual permission.

## 2. Owner authorization

The owner authorized this direction on 2026-07-31: the TradingView Advanced Chart script may run **only inside a dedicated wrapper document on a separate origin**. Pepe embeds only that wrapper. The wrapper must not receive Telegram initData, Pepe session/authorization/cookie data, identifiers, or private query parameters.

## 3. Context and superseded direction

The direct-iframe C1 record remains historically correct: no qualifying single direct-iframe provider was found. Its restriction that excluded TradingView from further consideration is superseded only by this owner-approved isolated-wrapper direction. TradingView has **not** thereby qualified as a direct iframe provider, received a rights approval, or been activated.

## 4. Goals

- Keep provider JavaScript and its nested widget frame outside the Pepe Mini App origin.
- Map fixed canonical Pepe values to documented TradingView values without arbitrary provider input.
- Preserve display-only behavior: no provider data enters Pepe.
- Define failure, rollback, privacy, security, and implementation boundaries before runtime work.

## 5. Non-goals

This PR creates no wrapper, iframe, provider enum, mapping, CSP, production configuration, account, key, DNS record, TLS certificate, proxy, ingestion, persistence, analytics, scraping, DOM access, message parsing, or Stage 9 capability.

## 6. Official TradingView integration mechanism

**Verified fact — official source:** [Advanced Chart: Widget Code & Settings](https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/) (accessed 2026-07-31) labels the widget `type: iframe` and generates HTML with a `tradingview-widget-container`, visible TradingView attribution, configuration JSON, and:

`https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js`

The generated configuration includes `symbol`, `interval`, `theme`, `locale`, `timezone`, and `autosize`; the displayed sample uses `interval: "D"`, `symbol: "NASDAQ:AAPL"`, `theme: "dark"`, and `autosize: true`. This is the **only approved future mechanism**: a static wrapper document loads that exact documented script and allows the script to create its own nested frame. Before production activation, W2/W5 must record an approved script-change detection approach, revalidate the complete subresource inventory when the documented script changes, and record an explicit keep-disabled/rollback decision before any reactivation. Host allowlisting alone does not establish that unchanged script content remains served.

**Rejected:** manually constructed TradingView iframe URLs, `tradingview-widget.com` URL construction, undocumented fragments, client-selected script URLs/symbols/intervals, provider script in the Pepe top-level document, or raw-data/message/DOM access.

## 7. Origin and trust-boundary model

| Boundary | Role | Mandatory restriction |
|---|---|---|
| Origin A — Pepe Mini App | Authenticated Telegram Mini App | It embeds only an approved Origin B URL with `referrerpolicy="no-referrer"`; it neither loads TradingView script nor reads a child DOM/window/message except for the narrow Origin-B lifecycle signals defined below. |
| Origin B — wrapper | Future dedicated public static wrapper origin | It is distinct from Origin A, accepts only canonical route segments, owns no Pepe authentication state, and has no access to Origin A DOM/storage. |
| Origin C — TradingView | Official script and nested widget origins | It is loaded only by Origin B. It has no access to Origin A DOM/storage and receives no Pepe identity, credential, or private parameter. |

Separate-origin isolation is mandatory. A parent iframe does not grant the wrapper access to Pepe DOM or storage; a cross-origin Pepe parent must not attempt to bypass that separation. No server-side proxy is permitted.

## 8. Wrapper route contract

**Proposed fixed shape:** `https://<approved-wrapper-origin>/chart/<canonical-slug>/<canonical-timeframe>`.

The wrapper maps only these local route values to an internal immutable table. It accepts no query string configuration, `postMessage` command channel, referrer-derived value, localStorage market selection, HTML, redirect, symbol, interval, script URL, theme, or locale input. Invalid paths render a neutral local error document and must not load TradingView.

**Preferred implementation:** static prebuilt route files, one per approved canonical pair, plus a minimal shared static template/build step. This is smaller and easier to audit than a client router; a future implementation may use a tiny static router only if hosting makes prebuilt routes impractical, with identical allowlisting and invalid-route behavior.

## 9. Canonical symbols

| Pepe slug | Proposed TradingView symbol | Verified source/semantics | Disclosure and gate |
|---|---|---|---|
| `btc-usdt` | `BINANCE:BTCUSDT` | **Verified fact:** the official [BTCUSDT symbol page](https://www.tradingview.com/symbols/BTCUSDT/) (accessed 2026-07-31) labels Bitcoin / TetherUS and Binance. This is an exchange crypto-spot pair, not BTC/USD. | Visible venue: Binance. Delay/entitlement remains unknown and must be shown as unknown until confirmed. |
| `eth-usdt` | `BINANCE:ETHUSDT` | **Reasonably supported:** same official symbol-page mechanism identifies ETHUSDT as Ethereum / TetherUS on Binance; final availability in the Advanced Chart must be tested in W2. | Visible venue: Binance. Delay/entitlement and regional availability remain unresolved. |
| `xau-usd` | `OANDA:XAUUSD` | **Verified fact:** the official [XAUUSD symbol page](https://www.tradingview.com/symbols/XAUUSD/) (accessed 2026-07-31) labels Gold Spot / U.S. Dollar and OANDA. | This must be disclosed as OANDA's broker/CFD/reference-style XAU/USD quote as applicable, **not** exchange-traded spot. Owner must confirm acceptance of the exact semantic disclosure before production. |

These are architecture proposals only, not runtime mappings or a representation that all regional entitlements exist. Official symbol pages are public-page evidence, not a TradingView rights grant or delay guarantee. Approved user fallback, if any, must use the official symbol-page route associated with the exact mapped symbol and must be separately allowlisted.

## 10. Canonical intervals

| Canonical timeframe | Proposed widget `interval` | Evidence and limitation |
|---|---|---|
| `1m` | `1` | **Reasonably supported:** Advanced Chart's generated configuration defines an `interval` field; live widget controls identify minute intervals. W2 must validate the exact value per mapped symbol. |
| `5m` | `5` | Same gate. |
| `15m` | `15` | Same gate. |
| `1h` | `60` | Same gate. |
| `4h` | `240` | Same gate. |
| `1d` | `D` | **Verified fact:** current generated Advanced Chart code uses `interval: "D"`; it is a chart interval, not a display-range button. |

A rejected/unsupported interval must produce a local unsupported-timeframe state; no date-range substitution, interval aggregation, or silent fallback is permitted.

## 11. Instrument semantics and disclosures

The visible product must show provider, source/venue, exact instrument semantics, and `delay unknown` unless an approved official disclosure establishes a different status. It must not call OANDA XAU/USD exchange-traded spot or represent any symbol as real-time without evidence. The display is informational only; it provides no market-data export, trading, advice, order routing, price referencing, or analytics.

## 12. Wrapper CSP

**Architecture result:** wrapper CSP is required but cannot be finalized from an interactive generated-widget page. W2 must capture the actual HTTPS-only subresource and redirect inventory using browser/network inspection without extracting provider data and derive the least-privilege policy.

Initial policy shape (placeholders, not deployable configuration):

- `default-src 'none'`
- `script-src https://s3.tradingview.com` plus only the minimum wrapper-owned static script/hash if needed
- `frame-src` limited to observed official HTTPS widget origins
- `connect-src`, `img-src`, `style-src`, `font-src`, and `media-src` limited only to observed required HTTPS origins
- `object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors https://<approved-pepe-origin> https://<approved-test-origin>; upgrade-insecure-requests`

No wildcard or HTTP source is approved. If host rotation forces a subdomain pattern, W2 must document the narrowest maintainable pattern and obtain separate security approval.

Required wrapper headers: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, restrictive `Referrer-Policy`, restrictive `Permissions-Policy`, HTTPS-only transport policy at hosting, and public static-file `Cache-Control` appropriate to versioned assets. Final `frame-ancestors` must name the owner-approved Pepe production origin and approved test origins; placeholders are intentional.

## 13. Pepe parent CSP

The future parent policy may add only `frame-src https://<approved-wrapper-origin>`. Pepe must not allow TradingView domains in its `script-src`, `frame-src`, `connect-src`, or other parent directives. The future parent iframe element must set `referrerpolicy="no-referrer"`; where applicable, the Mini App response policy must also use an equivalent restrictive `Referrer-Policy`. This protects the initial Origin-A-to-Origin-B navigation, before any wrapper response header applies: Origin B must not receive the Pepe document URL, Telegram parameters, session-related query values, or other private parent-navigation data. This PR makes no parent CSP or response-header change.

## 14. Iframe sandbox and permissions

The starting PoC candidate `allow-scripts allow-same-origin allow-popups` is **not approved**. W2 must test every token against the documented widget and report the minimum viable set.

- `allow-scripts`: expected necessary for the wrapper and official widget script; requires validation.
- `allow-same-origin`: not automatically approved for a generic wrapper. For the approved `postMessage` lifecycle-signaling path, it is required so Origin B retains a concrete origin and Pepe can enforce exact `event.origin` validation; without it, opaque-origin `null` events must be rejected. Separate-origin Origin B still cannot access Origin A, but retaining Origin B's own origin must be explicitly accepted by security review. An opaque-origin alternative is allowed only after a separately documented and security-reviewed signal design replaces this path.
- `allow-popups`: not automatically approved. It may be considered only for visible, user-initiated attribution/symbol navigation; `allow-popups-to-escape-sandbox` remains prohibited.
- `allow-forms`, `allow-modals`, `allow-downloads`, `allow-presentation`, `allow-top-navigation`, and `allow-top-navigation-by-user-activation`: prohibited unless a separately documented requirement and owner approval exists.

No `allow` permissions for camera, microphone, geolocation, clipboard, pointer lock, storage access, or fullscreen are approved. Attribution must remain visible and never navigate Pepe's top-level context.

## 15. Readiness model

A parent `load` event establishes only `wrapper-document-loaded`. It cannot prove nested TradingView rendering, data availability, symbol acceptance, regional availability, consent absence, or provider health.

Future state names are: `capability-loading`, `capability-error`, `wrapper-config-loading`, `wrapper-disabled`, `wrapper-not-configured`, `wrapper-loading`, `wrapper-document-loaded`, `readiness-unknown`, `provider-ready`, `provider-timeout`, `provider-blocked`, `provider-unavailable`, `offline`, `unsupported-instrument`, `unsupported-timeframe`, and `permanent-configuration-error`.

The future wrapper may emit a **narrow wrapper-owned lifecycle signal** to Pepe only for `wrapper-document-ready`, `provider-script-load-failed`, `provider-frame-created`, `provider-frame-document-loaded`, `provider-frame-timeout`, or `wrapper-configuration-invalid`. Pepe accepts it only when both `event.origin` is the exact approved wrapper origin and `event.source` is the currently mounted wrapper iframe window. There is no parent-to-wrapper command channel.

These signals contain only a fixed lifecycle name and configuration-version-safe metadata. They contain no price, candle, provider-extracted symbol, provider DOM content, identifier, credential, session, Telegram data, or arbitrary payload. Pepe must not parse TradingView-origin messages or inspect the nested TradingView frame. Wrapper code may observe only its own script load/error events, insertion of the provider frame element, and that frame element's lifecycle events.

`provider-frame-document-loaded` means only that the nested frame document loaded. It does not prove a usable chart, or that a regional block, consent, authentication, or provider-error page is absent. `provider-ready` remains unavailable unless TradingView later documents an official, origin-validated, non-market readiness signal that can be safely consumed; none is currently approved. Health therefore remains `readiness-unknown` after `provider-frame-document-loaded`.

## 16. Timeout and retry behavior

A future Mini App integration clears its **wrapper-document** timeout on parent frame load, then uses bounded wrapper lifecycle timeouts for script/frame creation. Observable `provider-script-load-failed`, missing/late provider-frame creation, or `provider-frame-timeout` may converge to generic `provider-unavailable`; `provider-frame-document-loaded` exposes `readiness-unknown`. Retry is user-triggered or bounded and remounts the parent wrapper iframe; it never creates a retry storm, automatic redirect, stale DEMO value, or synthetic fallback. Asset/timeframe controls stay usable.

## 17. Blocking and outage behavior

Offline, DNS/network failure, and wrapper-observable script/frame creation failures may converge to generic `provider-unavailable`. Cross-origin isolation cannot reliably observe nested content-level provider outages, regional blocks, consent pages, authentication pages, or error pages after the frame document loads; those remain `readiness-unknown` with visible attribution, honest limitation text, and a user-triggered fallback link. The UI must not assert a precise cause it cannot observe. A fallback link has no sensitive parameter, uses `noopener,noreferrer`, and is subject to the final owner-approved policy.

## 18. Kill switch and active-client invalidation

The approved future controls remain `EMBEDDED_CHART_ENABLED=false` or `MARKET_DATA_MODE=unavailable`. They affect future capability responses but do not remove already-mounted frames by themselves.

W3/W4/W5 must provide bounded capability polling plus focus/visibility revalidation and a server-defined capability version, or an explicitly validated equivalent. On capability withdrawal, an active client must unmount the wrapper, cease provider display requests, invalidate cached wrapper configuration, and render neutral unavailable state. Rollback is honestly **next-load only** until that live revalidation exists. Tests must cover both a fresh load and an active mounted client; neither may fall back to DEMO.

## 19. Privacy

No Telegram initData, authorization/session/cookie value, Telegram/user identifier, private query parameter, Pepe document URL, or Pepe storage is sent to Origin B/C. The parent iframe's mandatory `referrerpolicy="no-referrer"` prevents initial parent-navigation referrer disclosure to Origin B. Pepe does not read wrapper/TradingView DOM, inspect screenshots, parse TradingView messages, extract quotes/candles, proxy provider traffic, or persist provider data; it accepts only the fixed, Origin-B-validated lifecycle signals in section 15.

**Verified fact — official source:** [TradingView Privacy Policy](https://www.tradingview.com/privacy-policy/) (accessed 2026-07-31) says no account is needed for some public market viewing, but also describes cookies, web beacons, analytics, advertising, and third-party sharing for services. Thus the wrapper must neither claim tracker-free behavior nor forward Pepe identity; final production notice/consent obligations remain legal/privacy review gates.

## 20. Observability

Allowed future privacy-safe events: wrapper configuration requested, iframe mounted, wrapper document load callback, fixed wrapper lifecycle event, timeout, retry, fallback clicked, disabled, generic unavailable, capability version changed, and wrapper unmounted by kill switch. Do not log credentials, identifiers, cookies, referrer values, full potentially sensitive URLs, TradingView DOM/messages, prices, candles, screenshots, or extracted symbol content. Metrics must distinguish `wrapper document loaded`, `provider-frame-document-loaded`, and `provider ready`.

## 21. Attribution and fallback navigation

**Verified fact:** generated Advanced Chart markup includes an attribution link and `by TradingView`. W2 must preserve the current generated attribution/branding and confirm it remains visible at phone/desktop sizes. The wrapper must not crop, hide, overlay, or remove it. Any symbol or fallback navigation must be user-initiated, non-sensitive, and must not top-navigate Pepe.

## 22. Terms and public-display assessment

| Official source, accessed 2026-07-31 | Finding | Classification |
|---|---|---|
| [Advanced Chart docs](https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/) | Calls the Advanced Chart free and says it may be embedded in any website; generated code includes attribution. | Provider claim / reasonably supported technical embedding evidence. |
| [Terms of Use](https://www.tradingview.com/policies/) | Section 3 describes content/market data as display-only, limited to personal or internal business purposes, and prohibits non-display use, automated trading, processing, and products/services based on TradingView content. Terms may change without notice. | **Material ambiguity/conflict.** Formal terms control over widget marketing. |
| [Privacy Policy](https://www.tradingview.com/privacy-policy/) | Describes public viewing without an account for some markets and cookies/web beacons/analytics/advertising. | Explicit privacy disclosure; not a project-specific approval. |

**Terms result:** written TradingView confirmation is required before production. The free informational public Telegram Mini App may be read as outside “personal or internal business purposes” and/or as a product based on content. Until written confirmation covers this display-only wrapper, required attribution, proposed symbols, public-facing use, and applicable region/entitlement restrictions, production activation is blocked. This document makes no legal conclusion, representation, or acceptance on the owner's behalf.

## 23. Regional availability

Availability in Russia/DPR is unverified. The available test environment reached official docs and public symbol pages, but this is not Russia/DPR evidence and does not prove widget access. No official provider statement specifically qualifying this project, region, or Telegram WebView was found in this research. No jurisdiction-specific bypass, product VPN instruction, or compliance/availability promise is permitted. Generic unavailable behavior is required.

## 24. Hosting, DNS, and TLS requirements

A separate HTTPS wrapper origin is mandatory. Exact hostname, platform, DNS owner/procedure, TLS issuer/management, operational owner, headers, deployment, incident response, and log retention are unresolved owner/infrastructure decisions. The wrapper must never redirect HTTPS to HTTP. No hosting, DNS, TLS, or production domain decision is made here.

## 25. Telegram Android and Desktop validation

Architecture planning does not certify Telegram clients. W7 requires physical Telegram Android and Desktop tests for authentication isolation, responsive chart area, touch/scroll, all mappings/intervals, dark readability, visible attribution, popup behavior, safe fallback, offline/block/timeout/retry, active-client kill switch, back navigation, and no identity leakage. Optional iOS validation remains an owner decision.

## 26. Rollback

Future rollback sets the approved capability control to unavailable/disabled, confirms new loads receive no wrapper configuration, and after active revalidation exists unmounts active wrappers. Verify fresh load and active-client behavior, provider request cessation, no stale frame, no DEMO fallback, and no automatic re-enable until root cause, terms change, and owner approval. A terms/public-display change or loss of the mandatory written TradingView confirmation requires this rollback path.

## 27. Planned implementation pull requests

1. **W1 — Wrapper architecture qualification:** this documentation-only PR. Stop before merge.
2. **W2 — Static isolated wrapper foundation:** delivered by the current focused PR; see [`apps/tradingview-wrapper/README.md`](../apps/tradingview-wrapper/README.md) and [W2 validation evidence](tradingview-wrapper-w2-validation.md). It remains PR-only until owner merge approval; no Mini App integration or production DNS. Stop before merge.
3. **W3 — Backend wrapper configuration contract:** provider enum, wrapper-origin configuration, allowlisted routes, successful versioned config response, startup validation, no arbitrary URL/symbol. Stop before merge.
4. **W4 — Mini App wrapper integration:** dashboard and `/markets`, `referrerpolicy="no-referrer"`, validated wrapper-lifecycle handling, timeout/retry/fallback, capability revalidation, no quote/candle requests or DEMO fallback. Stop before merge.
5. **W5 — CSP, blocking, and rollback hardening:** exact parent `frame-src`, parent response referrer policy, sandbox, effective-header tests, observed script-change/subresource revalidation and explicit rollback decision, observable/unobservable failure handling, active-client kill switch, rollback exercise, privacy-safe telemetry. Stop before merge.
6. **W6 — CI main-push hardening:** CI on PR and `main` push, exact-main evidence, remediation procedure; merge before production activation. Stop before merge.
7. **W7 — Telegram validation and production activation:** mandatory written TradingView confirmation for intended public display; dedicated production wrapper origin, DNS/TLS, Android/Desktop smoke, production configuration, kill-switch exercise, and launch checklist. Stop before merge.

## 28. Acceptance criteria

Before any production activation: W1 is merged; official script remains documented and runs only inside the separate-origin wrapper, never Pepe's top-level document; W2 proves canonical route allowlisting and HTTPS behavior; approved exact mappings/intervals and accepted XAU semantics; mandatory written TradingView confirmation for intended public display; full domain/subresource inventory; narrow wrapper CSP and parent frame-only CSP; parent `referrerpolicy="no-referrer"` and equivalent restrictive parent response policy where appropriate; accepted sandbox including a concrete-origin lifecycle-signaling path; approved script-change detection with revalidated subresource inventory and explicit keep-disabled/rollback decision; validated wrapper lifecycle signaling with documented readiness limits; visible attribution; no identity flow or extraction; timeout/block/rollback/active invalidation evidence; W6 merged with green exact-main CI; W7 Android/Desktop evidence; and Stage 9 unchanged.

## 29. Unresolved owner decisions

- Exact production wrapper hostname, hosting platform, DNS owner/procedure, and TLS management.
- Exact Pepe production origin(s) for wrapper `frame-ancestors`.
- Acceptance of OANDA XAU/USD semantics and final visible disclosure.
- Fallback-link policy and whether visible attribution links may open popups/require `allow-popups`.
- Production activation date, physical iOS requirement, and privacy-safe wrapper metric retention.

## 30. Stage 9 boundary

Stage 9 belongs to Zheka and is excluded. This architecture permits no market-data extraction, ingestion, storage, analytics, reports, alerts, indicators, inference, or machine-readable use of TradingView content.
