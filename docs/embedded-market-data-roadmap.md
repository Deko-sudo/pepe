# Embedded market-data mode roadmap

> **Status:** PROPOSED — OWNER APPROVAL REQUIRED. This document is a planning contract only. It selects no provider, grants no license, adds no credentials, and authorizes no application work or Stage 9 work.

## 1. Executive summary

Pepe can offer an almost-zero-recurring-cost launch path by displaying an **official third-party embedded chart** in the Mini App while keeping server-side market data in `demo` mode. The widget is display-only: Pepe must not extract, scrape, intercept, persist, analyze, export, or re-publish the widget's quote/candle data.

The proposed candidate for an owner decision is TradingView's official Advanced Chart widget, because its official widget documentation describes an iframe/widget integration and its public symbol pages presently expose BTCUSDT and XAUUSD. This is technical feasibility evidence only. It is **not** evidence of a right to use the product, a guarantee of symbol availability, real-time entitlement, compatibility in Telegram WebViews, or availability in Russia/DPR. Those points remain **OWNER OR PROVIDER CONFIRMATION REQUIRED** before implementation or launch.

The implementation preserves Stages 1–8 and separates three explicit modes:

- `demo`: deterministic synthetic test/development data, labelled DEMO.
- `embedded`: provider-owned chart display only; no machine-readable market data enters Pepe.
- `live`: future authorized server-side normalized data, persistence, analytics, reports, and notifications.

No mode may silently substitute data from another mode. A missing capability is shown as unavailable, never synthesized.

## 2. Owner constraints and non-negotiable rules

**FACT — owner context:** Russian Federation / Donetsk People's Republic; launch market-data budget is preferably $0; AI and basic infrastructure costs have priority; users view information and statistics, not a market-data API or downloadable raw data.

**MUST NOT**:

1. Treat technical accessibility, a custom Telegram link, or a free Pepe product as permission to display or redistribute vendor content.
2. Scrape an iframe; inspect its DOM; intercept its requests; reverse engineer it; call undocumented endpoints; or persist/chart/compute from its data.
3. Send Telegram `initData`, Pepe cookies, fallback session headers, Authorization headers, session IDs, user identifiers, or secrets to a chart provider.
4. Show synthetic DEMO data as current/real market data or mix it with an embedded real chart without an unambiguous mode boundary.
5. Hide, crop, cover, reproduce, or remove mandatory provider branding/attribution.
6. Treat tokenized gold, futures, CFDs, XAU/USDT, or another gold product as equivalent to canonical `XAU/USD`.

**MUST**:

- fail closed to a safe unavailable state when the configured embedded provider, mapping, entitlement, CSP, or capability is not approved;
- preserve all existing session/security contracts and future provider interfaces;
- use direct, provider-owned navigation for an external fallback without appending sensitive query parameters;
- preserve exact provider/source, exchange/venue, delay, and instrument-semantics labels in the UI.

## 3. Verified baseline and repository map

**FACT — verified on 2026-07-30:** local `main` matched `origin/main` at `5cdf50571c5211852237db6b3104f679c326259c`; the worktree was clean; PR #12's decision document exists; no live provider implementation or Stage 9 implementation was found.

| Foundation | Current evidence | Embedded-mode disposition |
|---|---|---|
| Stage 1 technical foundation | Compose, API/worker settings, nginx and Vite app exist | Preserve; add a single explicit mode contract and CSP only in future PRs. |
| Stage 2 Telegram auth | `apps/mini-app/src/shared/telegram/provider.tsx`; server-side initData validation | Preserve unchanged; widget failure is isolated from auth. |
| Stage 3 users | authenticated Telegram-user persistence | Preserve unchanged; do not store third-party widget/user identity. |
| Stage 4 sessions | host-only session contract; protected API calls in `shared/api/market.ts` | Preserve unchanged; iframe receives no Pepe credentials. |
| Stage 5 catalog/mappings | canonical assets and provider mappings | Preserve canonical instruments; add a separate display mapping registry only if approved. |
| Stage 6 quotes | normalized quote/cache/persistence and current-quote UI | In embedded mode do not render server quote values as real. |
| Stage 7 candles | PostgreSQL `market_candles`, authenticated API, Celery queues/retries | Preserve schema/interfaces; embedded mode ingests and persists no widget candles. |
| Stage 8 UI | dashboard, markets route, chart, asset/timeframe controls | Main adaptation surface: replace only chart display according to capability mode. |
| Stage 9 | not present / owned by another stakeholder | No implementation; contract-only boundary below. |

Current synthetic pathways are explicit: `FakeQuoteProvider` in `apps/worker/app/quote_refresh.py`, `FakeHistoricalCandleProvider` in `apps/worker/app/candle_sync.py`, and worker schedules in `apps/worker/app/celery_app.py`. The API already rejects fake quotes in production (`apps/api/app/core/config.py`), but worker/Compose production behaviour requires a future explicit cross-service fail-closed policy. Existing worker Compose defaults enable fake providers, so the embedded production rollout cannot rely on defaults.

Current UI data coupling is in `apps/mini-app/src/pages/markets/index.tsx` and `apps/mini-app/src/features/market-home/market-home.tsx`: authenticated client calls fetch quotes and candles, and `MarketChart` renders stored candle data. Existing modes therefore need an explicit capability gate before a widget is introduced.

## 4. Official-source feasibility findings

### 4.1 Evidence consulted

| Source | Current finding | Decision consequence |
|---|---|---|
| TradingView widget catalogue: https://www.tradingview.com/widget/ | Page currently presents “Free Financial Widgets”. | Free access is not a license conclusion; vendor rights confirmation is still required. |
| TradingView Advanced Chart docs: https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/ | Official documentation currently presents the Advanced Chart widget and widget/iframe integration settings. | Candidate technically supports official embedding; validate the generated official snippet during PR B. |
| TradingView BTCUSDT symbol page: https://www.tradingview.com/symbols/BTCUSDT/ | Public page currently identifies BTCUSDT, including Binance venue examples. | Mapping must name an explicit venue, not generic BTC/USDT. Availability/legality is not verified. |
| TradingView XAUUSD symbol page: https://www.tradingview.com/symbols/XAUUSD/ | Public page currently identifies XAUUSD Gold Spot / U.S. Dollar with an OANDA venue example. | Candidate mapping is semantically closer to XAU/USD than tokenized gold, but venue and rights require approval. |
| Telegram Mini Apps: https://core.telegram.org/bots/webapps | Official documentation supports JavaScript Mini Apps in Telegram clients. | It does not certify any particular third-party iframe/widget. Android/Desktop must be smoke-tested. |
| CSP `frame-src`: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/frame-src | Documents the browser directive that limits frame sources. | Add a narrowly approved `frame-src` allowlist only after a provider/domain decision. |

### 4.2 Unresolved official-source points

The official pages above did **not** provide a complete, project-specific confirmation of commercial/non-commercial terms, mandatory attribution treatment, Russian Federation/DPR availability, Telegram Mini App permission, delay class, every timeframe, or every symbol/venue entitlement. Therefore all of the following are **OWNER OR PROVIDER CONFIRMATION REQUIRED**:

- current terms, permitted public embedding, commercial/display/redistribution scope, attribution/branding requirements, and change-without-notice risk;
- Russia/DPR access, sanctions/territorial restrictions, and any owner/deployment/user-jurisdiction restrictions;
- BTC/USDT, ETH/USDT, XAU/USD canonical mapping, exchange/venue semantics, supported intervals, real-time/delayed status, and widget interactivity;
- whether a chart may be displayed inside Telegram Android and Desktop WebViews;
- the exact third-party domains, frames, subresources, cookies/storage behaviour, `X-Frame-Options` and CSP requirements.

No claim about these items is made from technical reachability. No custom link changes the licensing analysis.

### 4.3 Alternatives

No alternative is recommended in this roadmap. A future owner-approved research request may compare **one or two official embeddable products only**, using the same legal, jurisdiction, attribution, symbol, timeframe, CSP, and Telegram acceptance gates. Avoid an unbounded provider survey.

## 5. Mode model and central capability matrix

### 5.1 Configuration pattern — PROPOSED

Introduce a typed runtime `MarketDataMode = demo | embedded | live | unavailable` plus a typed read-only frontend capability document. `unavailable` is a deliberate kill-switch state, not a data mode. API and worker startup MUST consume one shared, validated deployment-mode authority. The authenticated same-origin capability response is the only frontend authority; build-time public metadata may be cosmetic only and MUST NOT enable a capability. Missing, unknown, inconsistent, or mismatched runtime state resolves to `unavailable`. The frontend must never receive secret keys or make provider API calls. Provider-specific display mapping is data, not an API credential or a `provider_instrument_mappings` replacement.

Mode selection MUST be validated in API and worker startup. Production is invalid unless exactly one approved mode or the explicit `unavailable` kill switch is selected. `embedded` production is invalid if either fake worker path can write quotes/candles. The shared runtime authority must support an immediate transition to `unavailable`, and API, workers, scheduler, and frontend capability response must converge on that state before any chart capability is rendered.

### 5.2 Capability matrix

| Capability | `demo` | `embedded` | `live` | `unavailable` |
|---|---|---|---|---|
| Chart display | Pepe synthetic chart; visible DEMO | Official provider widget only, visible source/attribution | Pepe chart from authorized normalized candles | Unavailable state only |
| Quote cards | Explicit DEMO only outside production/demo environment | Hidden or chart-only until separately approved lawful source | Normalized authorized quote with provenance/freshness | Unavailable state only |
| Candle storage | Test/dev synthetic only | No widget ingestion or persistence | Authorized normalized PostgreSQL candles | No writes |
| Server analytics | Test fixtures only | Unavailable | Authorized source only | Unavailable |
| Reports | Clearly synthetic/test only | Pepe text/configuration only; no raw/widget export | Authorized data subject to rights | Unavailable/reduced state |
| AI commentary | Must know DEMO | Help/navigation only; no iframe-data claims | Authorized provenance-bearing data only | Help only; no market claims |
| Price notifications | Disabled except test harness | Disabled | Authorized machine-readable source only | Disabled |
| Historical data | Test/dev only | Unavailable | Authorized provider history | Unavailable |
| Attribution | DEMO label | Mandatory vendor branding/source/delay | Provider provenance/contractual attribution | No provider attribution |
| Offline/fallback | DEMO/unavailable label | Unavailable plus safe external link when approved | Stale/unavailable per freshness policy | Safe unavailable state; no synthetic substitute |

The UI must render mode and capability state before starting quote/candle queries. It MUST not use empty embedded responses to trigger a fake-data fallback.

## 6. Stage 1–8 adaptation roadmap

### Stage 1 — Technical foundation

**Preserve:** Docker topology, API/worker separation, Vite Mini App, nginx proxy and existing UI system.

**Future work:** typed shared runtime mode configuration; a narrow domain inventory; CSP response policy and test; explicit startup validation; authenticated runtime capability response; deterministic unavailable fallback. Do not add a broad wildcard CSP or disable security headers.

**Acceptance:** unknown mode fails startup or renders an authenticated safe unavailable state; no provider domains appear before owner approval; no migration.

### Stage 2 — Telegram initData validation

No functional auth change. The widget component is mounted only after the existing authentication flow succeeds, but chart load/timeout/blocked states must neither retry initData nor affect `TelegramProvider`. External links are constructed from an allowlisted base URL and canonical symbol/timeframe only; they must not include initData, fragment state containing initData, cookie values, fallback session headers, or user data.

### Stage 3 — Telegram-user persistence

No functional or schema change. Do not persist provider cookie IDs, widget telemetry identifiers, or inferred chart behaviour against a Telegram user. Any future preference storage requires a separate data-minimization decision.

### Stage 4 — Sessions and API authorization

No functional change to host-only cookies or fallback token handling. A cross-origin iframe cannot be a Pepe authenticated API client. Embedded mode requires an iframe-only provider document; vendor-hosted JavaScript MUST NOT execute in Pepe's top-level origin unless a separate owner-approved privileged-code security review expressly authorizes it. The iframe receives a static approved URL and never a `withSessionAuth()` request. Network tests must prove no `Authorization`, `X-Pepe-Session-*`, Cookie, initData, session ID, or user identifier leaves Pepe for an embedded-provider origin.

### Stage 5 — Asset catalog and provider abstraction

Preserve canonical slugs: `btc-usdt`, `eth-usdt`, `xau-usd`; canonical timeframes: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`.

**PROPOSED display mapping record:** `{ canonicalSlug, widgetProvider, widgetSymbol, venue, instrumentKind, displayLabel, supportedTimeframes, delayLabel, externalUrlTemplate, mappingVersion, approvalReference }`. Keep it separate from current/future server-side `provider_instrument_mappings` so a display widget is never mistaken for a licensed ingestion provider.

Mapping tests must reject missing venue, unsupported timeframe, unknown canonical slug, and non-equivalent XAU products. Examples such as `BINANCE:BTCUSDT`, `BINANCE:ETHUSDT`, and `OANDA:XAUUSD` are research candidates only, not approved production mappings.

### Stage 6 — Current quotes

**Safe policy choices requiring owner approval:**

1. **Preferred launch-safe policy:** embedded mode hides numeric quote cards and shows chart-only navigation with source, venue, delay/unknown-delay disclosure, and “data is displayed by provider” wording.
2. Replace cards with a neutral action that opens the chart/fallback link.
3. Add a separate lawful machine-readable quote source only through a later, separately approved live-mode contract.
4. Permit explicit DEMO cards only in a non-production demo environment; never alongside embedded charts as if both are live.

PR A MUST select, version, and test one discriminated unavailable response before PR C. For quote and candle capabilities unavailable in embedded mode, use HTTP `409`, `Cache-Control: private, no-store`, and `{ "code": "market_data_unavailable", "mode": "embedded", "capability": "quotes" | "candles", "reason": "not_available_in_mode" }`; empty or successful substitute responses are forbidden. `getQuote`, `getCandles`, `MarketChart`, and their API clients must consume that one contract consistently. Embedded mode must make current quote API use unnecessary for market UI. Loading, unavailable, delayed/unknown-delay, market-closed, unsupported, and provider-failure states have distinct labels. Never calculate bid, ask, mid, spread, 24h values, freshness, or price changes from the widget.

### Stage 7 — Candles and historical data

Preserve `market_candles`, authenticated candle endpoint, queue names, leases, retry model, `CandleTimeframe`, and live-provider extension points. In production embedded mode workers must not schedule/execute fake refresh/sync writes, and no widget data may enter PostgreSQL, Redis, or server analytics.

The candle endpoint's embedded-mode contract is the single versioned `market_data_unavailable` response selected in PR A, with HTTP `409` and `Cache-Control: private, no-store`; it is never an empty candle set or successful substitute. The frontend must switch to the embedded component before calling `getCandles`. Tests must prove zero widget-origin candle records, zero iframe extraction code, no accidental DEMO fallback, and intact future live interfaces. XAU session-aware expected-bar/gap validation remains a **live-ingestion prerequisite**, not an embedded workaround.

### Stage 8 — Real market UI adaptation

This is the principal future UI work.

**Component contract:** `EmbeddedMarketChart` accepts only approved display mapping, timeframe, non-secret presentation config, and callbacks for local retry/external navigation. It uses an iframe-only provider document with the strictest sandbox compatible with the approved widget; it has no vendor script in Pepe's top-level origin, `contentWindow`, DOM-read, message parsing, request interception, proxy, scraper, or data callback. A provider requiring top-level vendor JavaScript is blocked pending a separate privileged-code security review and owner approval.

**UX requirements:**

- asset selector and timeframe controls map only validated values;
- fixed/minimum mobile chart height and reserved container space prevent layout shift;
- safe-area top/bottom classes, touch targets, existing Prime Unit-style flat design, no attribution overlay;
- visible provider/source/venue and real-time, delayed, or `delay unknown` label;
- labelled skeleton, timeout, blocked iframe, unsupported WebView, network-offline, provider-unavailable, and unsupported-symbol/timeframe states;
- retry remounts only the widget and uses bounded attempts; it does not refetch synthetic data;
- external fallback is an accessible, user-initiated `noopener,noreferrer` navigation to an allowlisted provider URL;
- keyboard operability, focus-visible controls, screen-reader names/statuses, reduced-motion-safe skeleton/transition, and no auto-focus theft;
- Android and Desktop use the same semantic fallback contract but require physical Telegram smoke tests;
- dashboard and `/markets` both receive mode-aware rendering so neither can show a synthetic quote/candle next to an embedded chart as real.

**Visual QA acceptance:** BTC/USDT, ETH/USDT, and XAU/USD render the approved mapping at all six canonical timeframes; portrait narrow Android and Desktop width do not overflow; source and attribution remain visible in light/dark themes; every failure state is readable and has an external fallback; no layout jump after widget load; Tab/Shift+Tab and screen-reader order are coherent; reduced-motion mode removes nonessential animation.

## 7. Stage 9–12 ownership and data boundaries

### Stage 9 — Analytics core (owned by another stakeholder)

No Stage 9 work is permitted in this roadmap or its execution PRs. Embedded mode has no Pepe-owned normalized candles, so it cannot calculate/server-render EMA, ATR, RSI, FVG, volume, session, trend, or BTC-influence analytics. Built-in widget indicators are third-party UI only, not Pepe analytical results.

**Future handoff contract:** Stage 9 receives a capability object (`mode`, `serverCandlesAvailable`, `analyticsAvailable`, `dataProvenance`, `delayClass`, `unavailableReason`) and must render a clear unavailable state unless `live` provides authorized normalized candles. Migration to live changes the capability/data source, not the route or consumer UI contract.

### Stage 10 — Reports and publishing

Embedded reports may contain Pepe-owned copy, user configuration, and permitted attribution only. They must not claim ownership/analysis of unavailable data or copy/export raw widget values. Widget screenshots, exports, or embedded chart images require separate rights confirmation. Scheduled market reports must be unavailable/reduced in embedded mode until a machine-readable authorized source exists.

### Stage 11 — AI support and notifications

AI context must carry `market_data_mode`, provenance, capability state, and unavailable reason. In demo it must not call synthetic values real; in embedded it can provide help and navigation but must not claim iframe analysis. Market commentary, alerts, and price notifications require an authorized machine-readable live source. Missing data fails closed: no inference from chart pixels or user-visible widget text.

### Stage 12 — Production hardening and launch

Production embedded mode requires: explicit validated mode; fake quote/candle write paths disabled and independently tested; owner-approved CSP/domain inventory; attribution/branding compliance; privacy notice; outage monitoring without sensitive logs; safe external links; iframe fallback; jurisdiction/terms review; Android/Desktop smoke; rollback to unavailable state; and a documented live-mode migration path. Do not assume third-party cookies, storage, telemetry, or availability are supported; document observed behaviour without user/authentication data.

## 8. Sequential implementation pull requests

All PRs below are **PROPOSED**. Every PR stops before merge until owner decisions and exact-head CI/review are green. No PR may start Stage 9.

### PR A — Embedded-mode architecture and capability flags

- **Objective:** define mode enum, non-secret capability model, startup validation, and explicit unavailable contracts.
- **Allowed:** API/worker/frontend configuration types; mode-aware API schemas/errors; unit tests; architecture docs.
- **Forbidden:** widget, provider calls, credentials, provider mappings, persistence migration, Stage 9.
- **Expected areas:** API/worker settings, Mini App capability client/provider, market endpoint contracts, tests, Compose defaults only when implementing fail-safe validation.
- **Migrations:** none expected.
- **Tests:** all four states (`demo`, `embedded`, `live`, `unavailable`); unknown/inconsistent mode fails closed; one versioned HTTP 409 `market_data_unavailable` response contract with body/cache semantics across API clients and chart consumers; API capability/quote/candle mode responses; no production fake writes.
- **Manual smoke:** demo regression; embedded mode shows unavailable placeholder, no iframe; live mode remains unavailable without an authorized provider.
- **Security:** no secret in public config; mode cannot downgrade to demo; no session regression.
- **Acceptance/rollback:** independently deployable, feature disabled by default; a tested shared runtime transition selects explicit `unavailable`, not fake data.
- **Dependencies/stopping point:** owner approves mode model and fake-provider policy; stop before any external domain or widget integration.

### PR B — Embedded display mapping and chart component

- **Objective:** integrate one owner-approved official widget display mapping and `EmbeddedMarketChart`.
- **Allowed:** canonical-to-widget display mapping, component, attribution, approved official URLs, mapping/timeframe tests.
- **Forbidden:** quote/candle extraction, proxies, scraping, server persistence, API key, Stage 9, hidden branding.
- **Expected areas:** Mini App market feature/pages/styles/tests and mapping module; no backend provider adapter.
- **Migrations:** none.
- **Tests:** mapping validation; unsupported mapping; iframe static src generation; attribution; no sensitive URL/query fields; timeout/blocked/offline/fallback.
- **Manual smoke:** Telegram Android and Desktop against an owner-approved test environment.
- **Security:** strict allowlist; no `postMessage` data ingestion; no iframe DOM access.
- **Acceptance/rollback:** visible attribution and external fallback; failure remains safe; feature flag/mode disables component instantly.
- **Dependencies/stopping point:** written provider/jurisdiction/attribution decision and PR A merged; stop after chart-only display.

### PR C — Stage 6 and Stage 7 safety adaptation

- **Objective:** prevent mixed synthetic/embedded display and enforce no ingestion in embedded production mode.
- **Allowed:** mode-specific quote/card/candle endpoint/frontend behaviour, worker schedule guards, tests, documentation.
- **Forbidden:** live provider adapter, data migration, widget extraction, analytics, Stage 9.
- **Expected areas:** market pages/home, API market modules/schemas, worker configuration/schedule, Compose production validation, tests.
- **Migrations:** none expected; preserve existing PostgreSQL schema.
- **Tests:** quote-card policy; candle unavailable response; no DEMO fallback; fake-provider fail-closed; existing demo regression; no embedded persistence.
- **Manual smoke:** switch modes in non-production with clean UI boundaries; inspect browser request destination/headers without credentials.
- **Security:** no embedded origin receives Pepe tokens; workers cannot write fake records in embedded production.
- **Acceptance/rollback:** all unavailable states clear; revert mode to safe unavailable; no data deletion.
- **Dependencies/stopping point:** PRs A/B merged; quote-card decision approved; stop before live data.

### PR D — Telegram compatibility and UX completion

- **Objective:** validate CSP/WebView UX and accessible fallback behaviour.
- **Allowed:** CSP headers/allowlist, responsive styles, accessibility, telemetry without user/auth secrets, integration tests/docs.
- **Forbidden:** broad wildcards, credential forwarding, DOM extraction, provider implementation, Stage 9.
- **Expected areas:** nginx/hosting security headers, Mini App styles/components/tests, operational docs.
- **Migrations:** none.
- **Tests:** CSP, no session/initData leak, responsive/reduced-motion/a11y, blocked/provider/network/timeout paths, external link.
- **Manual smoke:** real Telegram Android and Desktop, light/dark, poor network/offline.
- **Security:** headers reviewed per approved domain inventory; links use allowlisted destinations.
- **Acceptance/rollback:** provider blocked still leaves navigation/fallback; CSP can be rolled back with feature disabled, never widened blindly.
- **Dependencies/stopping point:** PR C merged; provider-domain CSP and device results approved; stop before production launch.

### PR E — Production readiness and Stage 9 handoff

- **Objective:** complete release checklist, observability, rollout/rollback documentation, and capability handoff.
- **Allowed:** tests, docs, non-sensitive operational metrics, release checklist, handoff contract.
- **Forbidden:** Stage 9 code, market analytics, paid/live provider, credentials, report/notification implementation.
- **Expected areas:** tests, docs, health/observability boundaries, deployment validation.
- **Migrations:** none.
- **Tests:** full root gates plus mode matrix and regression suite.
- **Manual smoke:** production-like provider outage/fallback, both Telegram clients, attribution and privacy review.
- **Security:** log redaction review, fake fail-closed proof, no secret/config leakage.
- **Acceptance/rollback:** launch only after owner launch gate; rollback disables embedded display and presents unavailable state.
- **Dependencies/stopping point:** PR D merged and all owner gates complete; stop before Stage 9.

## 9. Test strategy

Automated future coverage must include:

1. Mode configuration validation and capability matrix unit tests.
2. Canonical symbol and timeframe mapping tests, including XAU equivalence rejection.
3. Quote-card and candle-API behaviour per mode.
4. Fake-provider production fail-closed tests against effective production configuration and deployment/profile overrides, not defaults alone: when `embedded` is selected, independently supplied quote and candle fake flags are both rejected across API, scheduler, direct worker entry points, and Compose/deployment-derived settings.
5. CSP/domain allowlist tests; no arbitrary frame source.
6. URL/request construction tests proving no session header, cookie, initData, token, user identity, or provider key is sent to a widget/fallback origin.
7. Static/code-level tests prohibiting iframe DOM read, `contentDocument`, provider request interception, and data-persistence paths in embedded component scope where practical.
8. Widget lifecycle tests: skeleton, bounded timeout, blocked iframe, unavailable provider, unsupported mapping, offline/network failure, retry, and external fallback.
9. Accessibility, keyboard, focus, screen-reader, responsive, safe-area, and reduced-motion tests.
10. Regression tests for Telegram auth, existing DEMO behaviour, quote core, candle schema/queues, and future live-mode capability compatibility.

Automated browser tests do **not** prove Telegram device compatibility. Manual acceptance requires real Telegram Android and Telegram Desktop smoke results with version/device/network recorded without sensitive data.

## 10. Security, privacy, compliance, rollout, and rollback

### Security model

- Same-origin Pepe API keeps current session/auth model; third-party widget is isolated in a cross-origin, iframe-only provider document. Vendor JavaScript must not execute in the Pepe top-level origin without a separate privileged-code approval.
- Only approved frame/source domains are allowed; no wildcard CSP and no arbitrary mapping URL.
- No provider credentials are used in embedded mode. No iframe scrape/proxy/network interception is permitted.
- External links are generated from static allowlisted templates and canonical display mapping; user input cannot select a host.
- Logs/metrics record mode, non-sensitive mapping version, provider availability and error class only; never initData, session tokens, cookies, Authorization, user identifiers, or raw auth payloads.

### Compliance and attribution

Keep provider attribution/branding visible. Before launch, retain a dated official terms/permission record and owner decision for display, commercial/non-commercial treatment, redistribution boundaries, privacy/tracking disclosure, Russian/DPR availability, symbol/venue/timeframe/delay semantics, and fallback links. Provider terms/branding/symbol availability may change; monitor and revalidate before material releases.

### Rollout and rollback

Roll out in order: internal demo regression → owner-approved staging embedded test → Telegram Android/Desktop manual smoke → limited launch only after owner launch gate. Use a kill-switch mode transition to `unavailable`; do not roll back by enabling synthetic data in production. Preserve databases/candles; embedded mode writes none. Live migration later adds an authorized server source behind the same capabilities, with separate provider/legal approval and data-quality validation.

## 11. Risk register

| Risk | Effect | Required mitigation / gate |
|---|---|---|
| Terms, branding or attribution change | unlawful/non-compliant display | Dated official verification; owner approval; visible attribution; kill switch. |
| Russia/DPR/provider availability restriction | widget unavailable or prohibited | Provider/owner legal confirmation; no automatic alternative. |
| Telegram blocks iframe / CSP / X-Frame-Options | chart fails | Android/Desktop smoke; bounded timeout; external fallback. |
| Wrong symbol/venue/XAU semantics | misleading chart | Versioned mapping with instrument kind/venue tests and owner approval. |
| Delayed/composite/exchange-specific data | misleading freshness/price assumption | Visible provider/venue/delay or unknown-delay label; no Pepe quote card. |
| Third-party tracking/storage | privacy exposure | Domain inventory, privacy notice, provider confirmation; no Pepe identity forwarding. |
| Provider outage/network failure | no chart | Safe unavailable UI, retry, external fallback, observability. |
| Mixed DEMO and embedded display | user deception | Mode gating, no fallback, explicit labels, regression tests. |
| Stage 9 analytics assumes candles | fabricated analytics | Capability handoff; unavailable state until live source. |
| No persistence / no alerts | reduced product scope | Explicit product messaging; defer reports/alerts to live mode. |
| Future paid provider required | budget change | Owner budget gate and separate live-provider decision. |

## 12. Owner decision gates and definition of done

No response/timeout means **STOPPED / BLOCKED**; it never selects a provider or launches a mode.

1. Select one specific embedded provider only after current official terms, jurisdiction, and technical findings are reviewed.
2. Accept required attribution/branding and privacy implications.
3. Approve each canonical symbol/venue mapping and timeframes, especially XAU/USD semantics.
4. Choose embedded quote-card policy (preferred: chart-only/no numeric Pepe quote cards).
5. Approve external fallback wording/destination behaviour.
6. Approve exact provider-domain CSP allowlist after its inventory is reviewed.
7. Approve production fake-provider policy: embedded production must disable all fake quote/candle writes and fail closed.
8. Accept recorded Telegram Android and Desktop smoke results.
9. Approve launch readiness only after PR A–E, review, exact-head CI, legal/provider confirmation, and rollback test.

**Definition of done for the future roadmap execution:** all owner gates are explicit; every PR is independently reviewed/tested; production embedded mode cannot persist/extract third-party data or show DEMO values as live; attribution and fallback remain visible; both Telegram client smokes pass; observability is non-sensitive; rollback has been exercised; and Stage 9 has only received its capability contract, not an implementation.

## 13. Explicit exclusions

This roadmap does not implement an embedded widget, select/purchase a provider, request/store credentials, alter fake-provider settings, add an iframe allowlist, modify application code, create migrations, begin Stage 9, merge a PR, or represent third-party data as Pepe-owned data.
