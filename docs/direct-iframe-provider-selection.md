# Direct-iframe chart-provider qualification results (PR C1)

> **Decision status:** NO QUALIFIED SINGLE PROVIDER — OWNER DECISION REQUIRED. This document is research and a proposed decision record only. It does not select, integrate, enable, license, or endorse a provider.
> **Research date:** 2026-07-31. Official sources were accessed on this date from an ordinary unauthenticated test environment. Where a provider returned an access challenge or unavailable page, that is recorded as an observation, not a regional conclusion.
> **Scope:** One provider must deliver public, display-only direct HTTPS iframes for exact BTC/USDT, ETH/USDT, and spot XAU/USD at candle intervals `1m`, `5m`, `15m`, `1h`, `4h`, and `1d`.
> **Historical update:** after this C1 result, the owner approved a distinct [isolated TradingView wrapper architecture](isolated-tradingview-wrapper-architecture.md). That later decision supersedes this document's direct-iframe restriction only; it does not rewrite the C1 evidence or establish a direct-iframe qualification.

## 1. Decision status

No candidate proved every mandatory requirement. No provider was selected under this direct-iframe qualification.

**Current split-provider decision:** a split-provider architecture is **not acceptable for C1**. The owner expressly withheld authorization for it, and the approved roadmap requires one provider decision before C2. A split would create two unapproved third-party trust, availability, attribution, privacy, CSP, redirect, outage, and mobile-validation surfaces, while also requiring a different configuration and rollback contract. It is not a harmless fallback for a failed single-provider search.

The narrowest next owner decision is whether to authorize a separately scoped split-provider qualification, relax one other hard constraint (exact USDT pairs, exact spot XAU/USD, all six native candle intervals, or direct-iframe-only architecture), or fund/approve a separately researched account-based provider. A split-provider authorization would first require all individual-provider C1 requirements, an explicit mapping of which provider serves which Pepe slug, independent public-display rights and attribution, exact domains/redirects, separate restrictive sandbox/CSP assessments, combined Telegram Android/Desktop validation, combined outage/kill-switch/rollback tests, and owner approval of the added security and operational surface. This PR must not be treated as approval for any relaxation.

## 2. Research date and scope

The review used current official provider pages for embed mechanism, terms/usage language, pricing/support where available, and product coverage. Sources are classified as **verified fact** (directly visible official material), **provider claim**, **technical observation**, **inference**, or **unresolved ambiguity**. Terms evidence is classified as explicit, reasonably supported, ambiguous, conflicting, or absent; it is not legal advice.

## 3. Mandatory requirements

A candidate needed all of the following, without substitutions: officially documented direct HTTPS iframe; no provider script in Pepe's top-level document or undocumented URL construction; exact allowlistable origin; no client credential/proxy/extraction; exact BTC/USDT and ETH/USDT economic instruments; spot XAU/USD (not futures, ETF, tokenized gold, XAU/USDT, or an undisclosed derivative); native candle intervals `1m`, `5m`, `15m`, `1h`, `4h`, `1d`; public-display rights clear enough for a free informational Mini App; implementable attribution; acceptable restrictive sandbox/CSP posture; and no identity/session forwarding.

A date-range control or refresh cadence is not a candle interval. Hard failures override score.

## 4. Candidate discovery

Nine plausible products were reviewed: MetalCharts, CoinGecko Widgets, TradingView (excluded baseline), CoinMarketCap Widgets, Investing.com Webmaster Tools, CryptoCompare, Twelve Data, Barchart, and FINVIZ. The first three were mandatory candidates. The final six additional candidates were included because they publicly market market-data charts/widgets or chart/data products; their quick pass found no official evidence of the required single-provider direct-iframe contract.

## 5. Disqualified candidates

| Candidate | Official-source evidence consulted (accessed 2026-07-31) | Result and hard failure |
|---|---|---|
| MetalCharts | [MetalCharts home](https://www.metalcharts.com/) | **Technical observation:** the current landing document uses a frameset that points to `http://www.machinest.com/keywordleasing/futuresframe.htm`; the advertised content is metal commodities **futures** charts. It fails HTTPS-only delivery and exact spot XAU/USD, and no official current widget contract proved exact USDT pairs or six candle intervals. |
| CoinGecko Widgets | [CoinGecko widgets](https://www.coingecko.com/en/widgets), [widget origin](https://widgets.coingecko.com/) | **Technical observation:** the official widget page/origin returned HTTP 403 from the unauthenticated test environment. The accessible official materials did not prove a direct iframe contract for all three instruments or deterministic native intervals. CoinGecko's crypto-widget scope also does not prove spot XAU/USD. Fails evidence and instrument requirements. |
| TradingView (excluded C1 baseline) | [Advanced Chart widget docs](https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/), [widgets catalogue](https://www.tradingview.com/widget/) | **Verified fact:** official docs label Advanced Chart `type: iframe` and provide generated embed code. **Historical C1 owner constraint:** TradingView was not authorized for direct-iframe selection. A subsequent owner decision approves only the separate-origin wrapper architecture linked above; it does not qualify TradingView as a C1 direct-iframe provider. |
| CoinMarketCap Widgets | [CoinMarketCap ticker widgets](https://coinmarketcap.com/widget/ticker/) | **Verified fact:** official page markets cryptocurrency ticker widgets. It does not prove exact spot XAU/USD or all six native candle intervals in a single chart contract. Fails required instrument/timeframe evidence. |
| Investing.com Webmaster Tools | [Investing.com Webmaster Tools](https://www.investing.com/webmaster-tools/), [Terms](https://www.investing.com/terms-and-conditions) | **Verified fact:** official page markets tools including technical charts and crypto/currency widgets. **Explicit terms conflict:** its public page states that use, storage, reproduction, display, modification, transmission, or distribution of data is prohibited without explicit prior written permission. No owner/provider written permission is available. Fails usage-rights clarity. |
| CryptoCompare | [CryptoCompare API documentation](https://min-api.cryptocompare.com/documentation) | **Technical observation:** current official documentation access returned HTTP 401 in the test environment. No official public direct-iframe chart contract was demonstrated; API documentation is not an iframe permission. Fails architecture evidence. |
| Twelve Data | [Twelve Data](https://twelvedata.com/), [tested widget route](https://www.twelve-data.com/widgets) | **Technical observation (accessed 2026-07-31):** the tested `https://www.twelve-data.com/widgets` host could not resolve in this test environment; accessible product materials do not establish a no-key public direct iframe covering all required assets/intervals. Fails architecture/access evidence. |
| Barchart | [Barchart](https://www.barchart.com/), [tested widgets route](https://www.barchart.com/widgets) | **Technical observation (accessed 2026-07-31):** the tested official `/widgets` route returned 404. No current official public direct-iframe contract was found for exact USDT pairs and spot XAU/USD. Fails architecture and instrument evidence. |
| FINVIZ | [FINVIZ](https://finviz.com/) | **Verified fact:** official product is a market screener/chart site. No official public direct-iframe widget documentation was found for crypto USDT pairs, spot XAU/USD, or the required intervals. Fails architecture and coverage evidence. |

## 6. Detailed finalist comparison

No candidate reached finalist status because each had at least one hard failure. The closest comparison remains informative but is not a recommendation:

| Requirement | MetalCharts | CoinGecko Widgets | TradingView baseline | Investing.com |
|---|---|---|---|---|
| Official direct iframe proven | No current HTTPS contract | Not proven | Official widget docs, but excluded | Not proven as a compliant direct iframe |
| BTC/USDT proven | No | No | Not assessed for selection | Not proven |
| ETH/USDT proven | No | No | Not assessed for selection | Not proven |
| Spot XAU/USD proven | No; futures framing observed | No | Not assessed for selection | Not proven |
| Six native candle intervals proven | No | No | Not assessed for selection | No |
| Usage rights | Absent/ambiguous | Absent/ambiguous | Not assessed for selection | Conflicting: prior written permission language |

## 7. Instrument semantics

No mapping is proposed. The research rejects BTC/USD and ETH/USD as substitutions for BTC/USDT and ETH/USDT. It also rejects futures, retail-gold products, tokenized gold, XAU/USDT, ETFs, and undisclosed derivatives as substitutions for spot XAU/USD. No candidate produced official evidence for all three exact semantics in one direct-iframe display product.

## 8. Timeframe semantics

No provider proved deterministic native candle intervals for all six values. The review distinguished candle interval from date range, chart duration, sampling, or refresh rate. Therefore all future mapping values remain unset.

## 9. Official embed mechanism

TradingView's official Advanced Chart documentation is the only mandatory-candidate official page observed to explicitly identify its widget as `type: iframe`; it is an excluded comparison baseline under the owner instruction. The remaining candidates either did not prove a current official direct-iframe contract in this research or failed another hard requirement. No provider URL pattern has been adopted.

## 10. Usage rights and attribution

No candidate has an approved public-display-rights result. Investing.com provides explicit restrictive language requiring prior written permission for display/reproduction/distribution of data, which controls over widget marketing. Other candidates' formal permission/attribution evidence is ambiguous or absent in this review. No attribution text is approved.

## 11. Cost and access

No cost/access profile is approved. The desired no-account/no-key/free profile remains a qualification preference, but it cannot compensate for hard architecture, instrument, interval, or rights failures. No account, paid plan, trial, key, or provider contact was used.

## 12. Data sources and delay

No provider supplied a qualifying, documented source/venue, spot-XAU methodology, and delay/cadence disclosure for all required mappings. No real-time claim is made; all delay disclosures remain unresolved.

## 13. Privacy and tracking

No candidate is approved for a privacy posture. The research did not send Pepe credentials, Telegram initData, user IDs, cookies, or Authorization values. A future provider PR must independently verify iframe storage/tracking, third-party subresources, referrer behavior, attribution navigation, and sandbox compatibility. No iframe market data was read, scraped, or persisted.

## 14. Exact domains and redirects

No production domains are approved. Observed technical evidence is limited to the public pages above. MetalCharts' current frameset has an HTTP child origin, which is disqualifying. CoinGecko's official widget origin returned 403 in this test environment. No redirect chain should be converted into runtime configuration from this document.

## 15. Sandbox and CSP assessment

No candidate passed a future sandbox/CSP assessment. For any future finalist, the required posture remains: exact HTTPS `frame-src` and optional fallback origin only; no provider `script-src`, broad `connect-src`, `unsafe-inline`, or `unsafe-eval`; restrictive referrer policy; and `sandbox` with no `allow-top-navigation`, `allow-top-navigation-by-user-activation`, `allow-downloads`, `allow-forms`, `allow-modals`, `allow-popups`, `allow-popups-to-escape-sandbox`, or `allow-same-origin` unless separately owner-approved with evidence. No `allow` attribute permission is approved.

## 16. Telegram WebView assessment

No physical Telegram Android or Desktop validation occurred because no provider qualified for technical validation. General browser accessibility is not Telegram certification. Future C6 must validate the selected provider in both physical clients.

## 17. Regional availability

**Regional availability: unverified.** Ordinary test-environment observations are not Russia/DPR evidence. The 403/401/host-resolution outcomes above are not attributed to regional policy. No bypass mechanism, VPN instruction, availability promise, or legal/compliance conclusion is made.

## 18. Technical validation evidence

No finalist survived the documentation gate, so no disposable iframe harness was created. This avoids testing undocumented provider URLs and avoids promoting a failed candidate into an implementation artifact. Browser checks were limited to public official pages without an authenticated Pepe session. No top-level provider script, iframe, DOM access, `postMessage` parsing, screenshot analysis, or market-data extraction occurred.

If a later provider qualifies, validation must record only `frame-document-loaded` and `readiness-unknown` unless the provider offers an approved origin-validated non-market readiness signal.

## 19. Scoring matrix

Scores are `0–5`, where `0` means no official evidence satisfies that category and `5` means current official evidence fully satisfies it. `EXCLUDED` means the owner prohibited selection before scoring. `UNPROVEN` means documentation access or scope did not establish the category. A hard failure is stated in the final column; only a hard failure prevents selection. Total does not override a hard failure.

| Candidate | Direct iframe | BTC/USDT | ETH/USDT | Spot XAU/USD | Six intervals | Rights clarity | Free/no-key | Sandbox/privacy | Docs/operations | Hard failure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| MetalCharts | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | HTTPS and exact-instrument failure |
| CoinGecko Widgets | UNPROVEN | UNPROVEN | UNPROVEN | 0 | UNPROVEN | UNPROVEN | 3 | UNPROVEN | 1 | contract/instrument/timeframe evidence absent |
| TradingView baseline | EXCLUDED | EXCLUDED | EXCLUDED | EXCLUDED | EXCLUDED | EXCLUDED | EXCLUDED | EXCLUDED | EXCLUDED | owner-excluded (not a technical hard-failure finding) |
| CoinMarketCap Widgets | UNPROVEN | 0 | 0 | 0 | 0 | UNPROVEN | 3 | UNPROVEN | 1 | required coverage absent |
| Investing.com | UNPROVEN | 0 | 0 | 0 | 0 | 0 | 3 | UNPROVEN | 2 | rights conflict |
| CryptoCompare | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 1 | no public direct-iframe proof |
| Twelve Data | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 1 | no public direct-iframe proof |
| Barchart | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | no current widget contract |
| FINVIZ | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 1 | no public direct-iframe proof |

**Scoring winner:** none. Every selection-eligible candidate has at least one hard failure; TradingView is separately owner-excluded and is not counted as a technical hard-failure conclusion.

## 20. Selected provider or no-qualified-provider conclusion

**No qualified single direct-iframe provider.** MetalCharts is not selected merely because it advertises charts: current official content observed is HTTP-framed metal futures material and does not prove exact USDT pairs, spot XAU/USD, six candle intervals, or rights. TradingView is not selected because the owner excluded it from C1 implementation selection.

## 21. Exact future provider mappings

None. The following fields remain deliberately unconfigured: provider, provider instrument identifier, interval mapping, iframe origin, fallback origin, attribution, source disclosure, delay disclosure, and configuration version.

## 22. Known limitations

- Public pages and official documentation can change; access evidence is dated.
- Access challenges and host-resolution failures are not proof of provider policy, regional restriction, or product unavailability.
- No legal conclusion is made. A later candidate still needs formal usage-rights and attribution analysis.
- No physical Telegram client test was appropriate without a qualifying candidate.

## 23. Production prerequisites

Before any implementation, the owner must approve a revised qualification boundary and a later C1/C2 evidence package must prove exact mappings, rights, domains, HTTPS redirects, security policy, attribution, source/delay disclosure, Telegram Android/Desktop validation, kill-switch/rollback behavior, and CI main-push hardening. The current provider-neutral fail-closed foundation remains authoritative.

## 24. Owner approval represented by merge

Merging this PR approves only the documented **no-qualified-provider conclusion** and preserves the existing fail-closed state. It does not select a provider or authorize C2–C6. A separate explicit owner decision is required before a new research or implementation branch.

## 25. Stage 9 boundary

Stage 9 belongs to Zheka and remains out of scope. This document authorizes no raw data extraction, persistence, analytics, indicators, reports, alerts, inference, or provider ingestion.
