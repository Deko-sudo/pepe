# Live Market Data Provider Decision Package

> **Status:** RESEARCH ONLY — NO PROVIDER HAS BEEN SELECTED OR IMPLEMENTED.
> **Date:** 2026-07-30
> **Baseline:** `main` @ `da9ee0e0` (PR #11 merged, Stage 8 complete)
> **Approval gate:** The owner must approve one architecture + provider before any implementation begins.

---

## 1. Verified Repository Baseline

| Field | Value |
|-------|-------|
| Base main SHA | `da9ee0e0f8f3688409868eba507d1abc4801c32a` |
| PR #11 state | MERGED (2026-07-30T14:00:50Z) |
| Post-merge CI | 9/9 green (run 30549637983) |
| Active quote provider | `FakeQuoteProvider` (synthetic, demo-labeled) |
| Active candle provider | `FakeHistoricalCandleProvider` (synthetic, demo-labeled) |
| Data mode | DEMO — deterministic synthetic prices via `blake2b(person=b"pepe-demo")` |
| Stage 9 | not started |

---

## 2. Current Synthetic-Provider Boundary

The worker hardcodes `FakeQuoteProvider(clock=...)` in `apps/worker/app/quote_refresh.py:220`
and `FakeHistoricalCandleProvider(clock=...)` in `apps/worker/app/candle_sync.py:162`.
No live provider is wired into the data path. Provider selection is gated by
`provider_key='fake'` in the SQL target loader. The `MarketDataProvider` /
`ProviderCapabilities` protocols in `apps/api/app/modules/market_data/providers.py`
exist as the intended adapter boundary but are not yet exercised.

**Config gates (enforce synthetic-only in production):**
- `quote_fake_provider_enabled` defaults `false`; raises `ValueError` if `true` in production.
- `candle_fake_provider_enabled` defaults `false`.
- `quote_source_label` / `quote_venue_label` must not be synthetic placeholders in production.

---

## 3. Exact Application Requirements

### Required instruments

| Slug | Symbol | Asset class | Calendar | Precision |
|------|--------|-------------|----------|-----------|
| `btc-usdt` | BTC/USDT | `crypto_spot` | always_open (24×7) | 2 / 8 |
| `eth-usdt` | ETH/USDT | `crypto_spot` | always_open (24×7) | 2 / 8 |
| `xau-usd` | XAU/USD | `metal_fx_spot` | provider_session (~23h weekdays) | 2 / null |

### Required candle intervals

`1m, 5m, 15m, 1h, 4h, 1d` (all six are native `CandleTimeframe` enum values).

### Candle contract

- UTC-aware timestamps; half-open interval `[open_time, close_time)`.
- Fully closed candles only — no future or incomplete bars.
- Deterministic identity: `(instrument_id, timeframe, open_time)`.
- PostgreSQL is the source of truth (table `market_candles`, unique constraint `uq_market_candles_identity`).
- Idempotent upsert via `ON CONFLICT (instrument_id, timeframe, open_time) DO UPDATE`.
- Candle sync service pages at 500 candles per request; rejects gaps, duplicates, and out-of-range bars.

### Quote contract

- `NormalizedQuote` (32 fields): price, bid/ask/mid, 24h OHLC/change, provenance, UTC timestamps, freshness policy.
- Latest-quote persistence: `latest_market_quotes` table, one row per instrument, idempotent upsert with deterministic latest-quote ordering.
- Freshness: crypto stale after 60s / hard-expire 300s; reference (XAU) stale after 300s / hard-expire 900s.
- Redis cache (best-effort, TTL 60s) sits in front of the DB.

---

## 4. Current Provider Interfaces (Exact Adapter Contract)

A live provider adapter must implement these structural protocols (Python `Protocol` — duck-typed, no base class):

### QuoteProvider

```python
async def fetch_quotes(
    self,
    requests: Iterable[QuoteRequest],
) -> tuple[NormalizedQuote, ...]
```

- Return exactly one `NormalizedQuote` per `QuoteRequest`, with matching `instrument_id`.
- All 32 `NormalizedQuote` fields populated and validated (positive prices, `bid ≤ ask`, `mid = (bid+ask)/2`, UTC timestamps, `stale_after_seconds > 0`, `hard_expire > stale_after`, deterministic `provider_event_id`).
- Failures: raise an exception (caught → `PROVIDER_FAILED` retryable → Celery backoff).

### HistoricalCandleProvider

```python
async def fetch_candles(self, request: CandleRequest) -> tuple[NormalizedCandle, ...]
```

- Return contiguous closed candles covering `[from_time, to_time]` inclusive (both aligned to timeframe boundary).
- `NormalizedCandle`: OHLC, optional base/quote volume, trade count, provenance labels, UTC timestamps.
- Service pages at 500 candles; validates alignment, contiguity, no gaps/duplicates.

### Wiring point

Replace `FakeQuoteProvider` / `FakeHistoricalCandleProvider` instantiation in
`quote_refresh.py:220` and `candle_sync.py:162`. Seed provider mappings in
`provider_instrument_mappings` and change the SQL filter from `provider_key='fake'`
to the live provider key.

### No interface change required

The existing `QuoteProvider` / `HistoricalCandleProvider` protocols are sufficient
for a live adapter. No interface extension is needed.

---

## 5. Candidate Elimination Table

| Provider | Category | Eliminated? | Reason |
|----------|----------|-------------|--------|
| Marketstack | Unified | **YES** | Equities/stocks only — no crypto, no forex, no XAU/USD. |
| Coinbase | Crypto | **YES** | Does not support USDT quote currency (uses USD/USDC). `BTC-USDC` ≠ `BTC/USDT`. |
| CoinGecko | Crypto aggregator | **YES** | No native 1m/5m/15m OHLCV (auto-granularity ≥ 30min; minute-grain is Enterprise-only). Cannot meet candle contract. |
| CryptoCompare / CoinDesk | Crypto aggregator | **YES** | Free tier retired 2026-05-21; paid-only with unknown pricing. Key-gated endpoints prevent verification. |
| MetalpriceAPI | Metals | **YES** | No documented intraday OHLC. Likely daily-only time-series. Insufficient for candle contract. |
| Metals-API | Metals | **YES** | OHLC endpoint is daily-only (UTC-day open/close). No native intraday candles (1m/5m/15m/1h/4h). |
| GoldAPI | Metals | **YES** | No intraday candle API. Daily OHLC in quote response only. Metals-only (no crypto). |
| Polygon.io / Massive | Unified | **MARGINAL** | Supports XAU/USD spot (forex) but crypto is USD-quoted only — **no BTC/USDT or ETH/USDT**. Viable only if owner accepts BTC/USD substitution. |

---

## 6. Viable Provider Comparison

### Unified single-provider candidates

| Criterion | Twelve Data | Alpha Vantage | Finnhub | Tiingo |
|-----------|-------------|---------------|---------|--------|
| BTC/USDT | ✅ `BTC/USDT` | ✅ `BTC,market=USDT` | ✅ `BINANCE:BTC/USDT` | ✅ `btcusdt` |
| ETH/USDT | ✅ `ETH/USDT` | ✅ `ETH,market=USDT` | ✅ `BINANCE:ETH/USDT` | ✅ `ethusdt` |
| XAU/USD spot | ✅ `XAU/USD` (Gold Spot) | ✅ `XAU→USD` | ✅ `OANDA:XAU_USD` | ✅ `XAU/USD` |
| Native 1m/5m/15m | ✅ | ✅ | ✅ | ✅ |
| Native 4h | ✅ | ❌ (aggregate from 1h) | ❌ (aggregate from 1h) | ❓ UNVERIFIED |
| Native 1d | ✅ | ✅ (separate daily endpoint) | ✅ | ✅ |
| Max rows/req | 5,000 | compact/full (UNVERIFIED) | UNVERIFIED | ~1 year window |
| WebSocket | ✅ (paid) | ❌ | ✅ | ✅ |
| Historical depth | 20+ years | UNVERIFIED | UNVERIFIED | ~2020+ |
| Free tier | 800 req/day, 8/min | 25 req/day | 60 req/min (forex OHLC is premium) | 1,000 req/day, 50/hr |
| Cheapest paid for all 3 | $29/mo (Grow) | $49.99/mo (75/min) | $49.99/mo (forex OHLC) | $10/mo (Power) — UNVERIFIED XAU |
| 24h change% | ✅ (rolling fields) | derive | derive | derive |
| Bid/Ask | ❌ (not in `/quote`) | ✅ | via candles | ✅ (top-of-book) |

### Crypto exchange candidates (for split architecture)

| Criterion | Binance | Bybit | Kraken |
|-----------|---------|-------|--------|
| BTC/USDT | ✅ `BTCUSDT` | ✅ `BTCUSDT` | ✅ `BTCUSDT` (→`XBTUSDT`) |
| ETH/USDT | ✅ `ETHUSDT` | ✅ `ETHUSDT` | ✅ `ETHUSDT` |
| 1m/5m/15m/1h/4h/1d | ✅ all native | ✅ all native | ✅ all native |
| Max candles/req | 1,000 | 1,000 | 720 |
| API key required | No (public market data) | No | No |
| 24h change% | ✅ `priceChangePercent` | ✅ `price24hPcnt` | ❌ (compute from open/last) |
| Bid/Ask | ✅ | ✅ | ✅ |
| WebSocket | ✅ | ✅ | ✅ (v2) |
| Rate limit | 1,200 weight/min (IP-based) | 600 req/5s (IP-based) | ~1 req/s safe (call counter) |
| Geographic restrictions | **US prohibited** (Binance.com) | UNVERIFIED | UNVERIFIED |
| Cost | Free | Free | Free |

### Gold/metals candidates (for split architecture — XAU/USD only)

| Criterion | Twelve Data | Massive (Polygon) |
|-----------|-------------|-------------------|
| XAU/USD spot | ✅ `XAU/USD` | ✅ `C:XAUUSD` (forex composite) |
| Native 1m/5m/15m/1h/4h/1d | ✅ all native | ✅ via multiplier/timespan |
| Max rows/req | 5,000 | 50,000 |
| Historical depth | 20+ years | 10+ years (paid); 2 years (free) |
| WebSocket | ✅ (paid) | ✅ |
| Cheapest paid | $29/mo (Grow) | $49/mo (Currencies Starter) |
| Also supports crypto | ✅ | ❌ (USD-quoted only) |

---

## 7. Official-Source Citations

| Provider | Official URL (verified) |
|----------|------------------------|
| Twelve Data pricing | https://twelvedata.com/pricing |
| Twelve Data XAU/USD | https://twelvedata.com/markets/300755/commodity/xau-usd |
| Twelve Data time-series docs | https://twelvedata.com/docs |
| Twelve Data terms | https://twelvedata.com/terms |
| Binance API spec | https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md |
| Bybit V5 docs | https://bybit-exchange.github.io/docs/v5/ |
| Kraken docs | https://docs.kraken.com/ |
| Kraken llms index | https://docs.kraken.com/llms.txt |
| Finnhub pricing | https://finnhub.io/pricing |
| Finnhub rate-limit docs | https://finnhub.io/docs/api/rate-limit |
| Alpha Vantage premium | https://alphavantage.co/premium/ |
| Alpha Vantage crypto list | https://alphavantage.co/cryptocurrency_list/ |
| Massive (ex-Polygon) pricing | https://massive.com/pricing |
| Massive rebrand announcement | https://massive.com/blog/polygon-is-now-massive/ |
| Massive forex aggregates docs | https://massive.com/docs/rest/forex/aggregates/custom-bars.md |
| Tiingo forex product | https://tiingo.com/products/forex-api |
| Tiingo crypto product | https://tiingo.com/products/crypto-api |
| Metals-API pricing | https://metals-api.com/pricing |
| GoldAPI | https://www.goldapi.io/ |
| CryptoCompare/CoinDesk free-tier retirement | https://data.coindesk.com/blogs/changes-to-coindesk-data-indices-api-free-tier-access |

---

## 8. Rate-Limit Calculations

Based on the actual Pepe scheduler design:
- Quote refresh: every 60s, 1 request per instrument
- Candle sync: every 300s, 1 paginated request per (instrument, timeframe) pair
- Candle page size: 500 max

### Request volume by profile

| Profile | Instruments | IT pairs | Active h/day | Quote req/day | Candle req/day | Total/day | Monthly (30d) | Worst-case (3× retry) |
|---------|------------|----------|-------------|---------------|----------------|-----------|---------------|----------------------|
| A — Local dev | 3 | 18 | 4 | 720 | 864 | 1,584 | 47,520 | 142,560 |
| B — Initial launch | 3 | 18 | 24 | 4,320 | 5,184 | 9,504 | 285,120 | 855,360 |
| C — Growth | 10 | 60 | 24 | 14,400 | 17,280 | 31,680 | 950,400 | 2,851,200 |

**Assumptions (labeled):**
- Per-symbol quote requests (worst case). Batch-capable providers reduce quote requests by 67–90%.
- Candle steady state: ~2 candles per TF per cycle (incremental, fits 1 page).
- Retry multiplier 3× is a worst-case assumption, not a measured value.
- Dev duty cycle 4h/day is a labeled assumption for intermittent local development.

### Cold-start backfill (one-time)

| Profile | Pages (bootstrap windows: 1m=24h, 5m=7d, 15m=30d, 1h=180d, 4h=365d, 1d=5y) |
|---------|------|
| A / B (3 instruments) | 96 pages |
| C (10 instruments) | 320 pages |

### 24-hour outage recovery

| Profile | Pages (24h of all TFs) |
|---------|----------------------|
| A / B (3 instruments) | 24 |
| C (10 instruments) | 80 |

---

## 9. Cost Models

### Profile A — Local Development

| Provider option | Plan | Monthly cost | Fit |
|----------------|------|-------------|-----|
| Twelve Data | Free (800 req/day) | $0 | ❌ exceeds 1,584/day |
| Twelve Data | Grow | $29 | ✅ unlimited daily, 55+ credits/min |
| Binance + Twelve Data (split) | Binance free + Twelve Data Grow | $29 | ✅ best value |
| Alpha Vantage | Free (25 req/day) | $0 | ❌ far too low |
| Alpha Vantage | 75 req/min | $49.99 | ✅ |
| Finnhub | Free (60 req/min) | $0 | ⚠️ forex OHLC is premium — XAU needs paid |
| Tiingo | Power | $10 | ❓ UNVERIFIED XAU intraday |

### Profile B — Initial Launch (3 instruments, 24×7)

| Provider option | Plan | Monthly cost | Fit |
|----------------|------|-------------|-----|
| Twelve Data | Pro | $99–$191 | ✅ 610+ credits/min, covers ~9,500 req/day |
| Twelve Data | Grow | $29 | ⚠️ marginal — 55 credits/min may bottleneck |
| Binance + Twelve Data (split) | Binance free + Twelve Data Grow | $29 | ✅ crypto is free; only XAU uses Twelve Data |
| Alpha Vantage | 150 req/min | $99.99 | ✅ |
| Finnhub | Lite ($49.99) | $49.99 | ⚠️ forex OHLC premium; UNVERIFIED tier needed |

### Profile C — Growth (10 instruments, 24×7, 2 workers)

| Provider option | Plan | Monthly cost | Fit |
|----------------|------|-------------|-----|
| Twelve Data | Ultra | $329–$832 | ✅ 2,584+ credits/min |
| Binance + Twelve Data (split) | Binance free + Twelve Data Pro | $99–$191 | ✅ crypto free; XAU on Pro |
| Alpha Vantage | 600 req/min | $199.99 | ✅ |
| Finnhub | All-In-One | $3,500 | ❌ prohibitively expensive |

---

## 10. Legal and Licensing Findings

> **All findings below are from official vendor pages where retrievable. Items not confirmed from official sources are marked UNVERIFIED and require direct vendor confirmation before production use.**

### Commercial use / redistribution

| Provider | Commercial on free? | Key restrictions |
|----------|--------------------|-----------------|
| Twelve Data | ❌ No (free tier bans commercial use) | Paid tiers: no redistribution without authorization; must delete data within 30 days of termination; storage retention limits "permitted timeframes" (UNVERIFIED per-tier) |
| Binance / Bybit / Kraken | ✅ Yes (public market data is free) | Data-use clauses UNVERIFIED in API docs; governed by general Terms |
| Alpha Vantage | UNVERIFIED | Terms as PDF — not retrievable; historically permits internal storage, restricts redistribution |
| Finnhub | UNVERIFIED | Terms JS-rendered — not retrievable; historically allows internal use |
| Tiingo | UNVERIFIED | Terms JS-rendered — commercial tiers permit internal use |
| Massive/Polygon | UNVERIFIED | Historically allowed internal storage/caching; redistribution requires business tier |

### PostgreSQL candle persistence

- **Twelve Data**: Terms mention "permitted timeframes" for caching — the exact retention window for paid tiers is **UNVERIFIED**. Storing OHLCV indefinitely in PostgreSQL may require vendor confirmation.
- **Binance/Bybit/Kraken**: Public market data is generally usable for internal storage. Specific clauses **UNVERIFIED** from API docs.
- **All providers**: Displaying prices inside a Telegram Mini App to your own users is typically "internal/display" use (permitted) rather than redistribution — but this requires per-vendor confirmation.

### Attribution requirements

- Twelve Data: attribution required when external display/redistribution is permitted.
- Others: UNVERIFIED from official pages.

### Key unresolved legal questions for vendors

1. Does the paid plan explicitly permit storing intraday OHLCV in PostgreSQL indefinitely?
2. Is displaying prices in a Telegram Mini App classified as "display" or "redistribution"?
3. What are the retention/deletion obligations on plan termination?

---

## 11. Architecture Options

### Option 1 — Single Unified Provider

**Description:** One vendor supplies all three instruments (BTC/USDT, ETH/USDT, XAU/USD) for both quotes and candles.

**Best candidate:** Twelve Data

| Aspect | Detail |
|--------|--------|
| Adapter count | 1 quote adapter + 1 candle adapter (or 1 unified) |
| Credentials | 1 API key |
| Quote path | `fetch_quotes` → NormalizedQuote for all 3 instruments |
| Candle path | `fetch_candles` → NormalizedCandle for all 3 × 6 TFs |
| Rate-limit handling | Single credit pool; 55+ credits/min (Grow) to 2,584+ (Ultra) |
| Scheduler impact | Minimal — same beat schedule, different provider instance |
| Data normalization | Single provenance namespace; consistent source labels |
| Attribution | Single "Twelve Data" source label |
| Backfill | `/earliest_timestamp` + date-range pagination; 20+ years depth |
| Outage behavior | No data for any instrument during provider downtime |
| Operational complexity | Lowest — 1 vendor relationship, 1 key, 1 adapter |
| Expected cost | $29/mo (Grow) → $99–$191/mo (Pro) → $329–$832/mo (Ultra) |
| Legal risk | Twelve Data retention clauses need vendor confirmation |
| Migration effort | Replace FakeProvider, seed mappings, update SQL filter |
| Test strategy | Adapter unit tests with mock HTTP; integration tests against sandbox/demo |

### Option 2 — Crypto Exchange + Separate XAU/USD Provider (Split)

**Description:** A crypto exchange supplies BTC/USDT and ETH/USDT (free public market data); a separate provider supplies XAU/USD.

**Best pairing:** Binance/Bybit (crypto) + Twelve Data (XAU/USD)

| Aspect | Detail |
|--------|--------|
| Adapter count | 2 quote adapters + 2 candle adapters |
| Credentials | 0 (crypto public) + 1 API key (XAU provider) |
| Quote path | Crypto: batch ticker endpoint → 2 NormalizedQuotes; XAU: Twelve Data `/quote` → 1 NormalizedQuote |
| Candle path | Crypto: klines endpoint → NativeCandles; XAU: Twelve Data time-series → NormalizedCandles |
| Rate-limit handling | Crypto: weight-based (Binance 1200/min, Bybit 600/5s); XAU: Twelve Data credits |
| Scheduler impact | Two provider instances; target loader splits by `provider_key` |
| Data normalization | Two provenance namespaces; crypto source = "Binance"/"Bybit"; XAU source = "Twelve Data" |
| Attribution | Two source labels visible in UI |
| Backfill | Crypto: `startTime`/`endTime` windows (deep history); XAU: Twelve Data date ranges |
| Outage behavior | Partial — crypto or XAU can fail independently; fallback possible |
| Operational complexity | Medium — 2 vendor relationships, but crypto is free and keyless |
| Expected cost | $0 (crypto) + $29/mo (Twelve Data Grow for XAU only) = **$29/mo** |
| Legal risk | Crypto terms UNVERIFIED; Twelve Data retention clauses need confirmation |
| Migration effort | 2 adapters; provider-key routing in target loader; mapping seeding |
| Test strategy | Per-adapter unit tests; integration tests against public endpoints (crypto) and sandbox (XAU) |

**Critical concern — Binance geographic restriction:** Binance.com prohibits US persons. If the deployment server or owner is in the US, Binance is unavailable. Bybit and Kraken are alternatives (geographic restrictions UNVERIFIED).

### Option 3 — Primary Provider + Fallback Provider

**Description:** A primary provider supplies all instruments; a secondary provider supplies the same instruments as a fallback when the primary is unavailable.

| Aspect | Detail |
|--------|--------|
| Feasibility | Only viable if both providers agree on instrument semantics |
| Key risk | Two providers may disagree on: daily candle boundaries (UTC vs exchange/session), price source (spot vs composite), volume meaning, timestamp precision, revised candles |
| Series-boundary safety | **Must NOT silently combine** candles from two providers into one continuous series. Provenance must mark the provider switch; series boundaries must be explicit. |
| Implementation | Requires provenance-aware candle stitching and quote-source-versioning |
| Operational complexity | Highest — 2 full adapters, health checks, failover logic, series-boundary handling |
| Recommendation | **Not recommended for initial launch.** Consider only after a single-provider solution is stable and the disagreement risks are quantified. |

---

## 12. Scoring Methodology

### Weighting (defined before scoring, not manipulated)

| Criterion | Weight | Rationale |
|-----------|--------|-----------|
| Exact instrument coverage | 15% | Must serve BTC/USDT, ETH/USDT, XAU/USD exactly |
| Candle/timeframe coverage | 12% | All 6 intervals must be native or safely aggregable |
| Timestamp/candle-contract compatibility | 10% | UTC alignment, closed-candle semantics, gap-free |
| Quote freshness | 8% | Update frequency and delay classification |
| Historical depth | 5% | Backfill capability |
| Rate-limit fit | 10% | Must handle Profile B within plan limits |
| Launch cost | 8% | Profile B monthly cost |
| Growth cost | 5% | Profile C monthly cost |
| Documentation quality | 5% | Official docs completeness and clarity |
| Operational reliability | 7% | SLA, status page, uptime track record |
| Legal/commercial clarity | 7% | Clear terms for storage, display, commercial use |
| Attribution burden | 2% | UI/integration labeling requirements |
| Credential security | 3% | Server-side key management, IP allowlisting |
| Implementation complexity | 3% | Adapter effort, normalization difficulty |

Each criterion scored 0–5. Weighted score = Σ(score × weight).

### Scoring results

| Criterion (weight) | Twelve Data | Binance+TD | Alpha Vantage | Finnhub | Bybit+TD | Kraken+TD |
|---------------------|:-----------:|:----------:|:------------:|:-------:|:--------:|:---------:|
| Exact instruments (15%) | 5 | 5 | 5 | 5 | 5 | 5 |
| Candle coverage (12%) | 5 | 5 | 3 | 4 | 5 | 5 |
| Contract compat (10%) | 5 | 5 | 4 | 4 | 4 | 4 |
| Quote freshness (8%) | 4 | 5 | 3 | 4 | 5 | 4 |
| Historical depth (5%) | 5 | 5 | 3 | 3 | 4 | 3 |
| Rate-limit fit (10%) | 4 | 5 | 4 | 3 | 5 | 3 |
| Launch cost (8%) | 4 | 5 | 3 | 3 | 5 | 5 |
| Growth cost (5%) | 3 | 4 | 4 | 1 | 4 | 4 |
| Documentation (5%) | 5 | 4 | 4 | 3 | 4 | 3 |
| Reliability (7%) | 4 | 4 | 3 | 3 | 4 | 4 |
| Legal clarity (7%) | 3 | 2 | 2 | 2 | 2 | 2 |
| Attribution (2%) | 3 | 3 | 3 | 3 | 3 | 3 |
| Credential security (3%) | 4 | 5 | 4 | 4 | 5 | 5 |
| Implementation complexity (3%) | 4 | 3 | 3 | 3 | 3 | 3 |
| **Weighted total** | **4.33** | **4.54** | **3.72** | **3.58** | **4.45** | **4.14** |

### Hard disqualifiers

- **Coinbase:** No USDT quote currency.
- **CoinGecko:** No native intraday OHLCV.
- **CryptoCompare/CoinDesk:** Free tier retired; paid-only with unverifiable pricing.
- **Metals-API / MetalpriceAPI / GoldAPI:** No intraday candle API.
- **Marketstack:** No crypto/forex/metals.

### Unresolved unknowns

- Twelve Data: exact PostgreSQL retention clause for paid tiers.
- Binance/Bybit/Kraken: geographic restrictions for the deployment server location.
- Binance/Bybit/Kraken: explicit data-storage/redistribution terms.
- Alpha Vantage / Finnhub / Tiingo: full Terms of Service (JS-rendered/PDF, not machine-retrievable).

### Confidence levels

- Twelve Data instrument/interval/cost data: **HIGH** (verified from official pricing + docs pages).
- Crypto exchange public endpoint behavior: **HIGH** (verified from official API specs and live probes).
- Legal/storage terms for all providers: **LOW** (terms pages largely unretrievable; requires human review).
- Provider reliability/uptime: **MEDIUM** (status pages exist but not deeply analyzed).

---

## 13. Recommendation (Advisory Only — NOT a Selection)

### Recommended architecture: Option 2 — Split Provider (Crypto Exchange + XAU/USD Provider)

**Rationale:**
- Crypto market data from Binance/Bybit is **free, real-time, keyless**, with all 6 native intervals and 1,000 candles/request.
- XAU/USD from Twelve Data provides **spot gold** with all 6 native intervals, 20+ years of history, and WebSocket streaming.
- Total cost: **$29/month** (Twelve Data Grow for XAU only; crypto is free).
- The split provides **partial outage isolation** — if the crypto exchange is down, XAU data continues, and vice versa.
- The split architecture is more resilient and cheaper than any single-provider option for the same coverage.

### Recommended primary pair: Bybit (crypto) + Twelve Data (XAU/USD)

**Why Bybit over Binance:** Binance.com prohibits US persons. Bybit's geographic restrictions are less documented but it does not have a published US prohibition equivalent to Binance's explicit ban. **The owner must confirm the deployment jurisdiction before final selection.** If the deployment is outside the US, Binance is equally viable and has deeper liquidity/longer history.

### Credible alternative: Option 1 — Twelve Data unified (single provider)

**When to prefer this:** If operational simplicity (1 vendor, 1 key, 1 adapter, 1 terms page) outweighs the cost savings of free crypto data. Twelve Data covers all three instruments natively, and the Pro tier ($99–$191/mo) handles Profile B with margin. This is the lowest-complexity path.

### Main risks

1. **Legal/storage terms UNVERIFIED** — Twelve Data's "permitted timeframes" caching clause and all providers' PostgreSQL storage rights need vendor confirmation before committing to indefinite candle persistence.
2. **Geographic restrictions** — Binance prohibits US access; Bybit/Kraken restrictions UNVERIFIED.
3. **Series-boundary safety** — If a split architecture ever needs fallback (Option 3), two providers' candle semantics may not be safely combinable.
4. **4h candle aggregation** — Alpha Vantage and Finnhub lack native 4h; aggregating from 1h introduces complexity and must match Pepe's `[open_time, close_time)` contract.

### Estimated implementation scope

- 1–2 adapter classes implementing `QuoteProvider` / `HistoricalCandleProvider`.
- Provider mapping seeding (Alembic migration for `provider_instrument_mappings`).
- Worker wiring changes (replace `FakeProvider` instantiation, update SQL target filter).
- Config additions (API keys as env vars, provider selection toggle).
- Unit tests with mocked HTTP; integration tests against sandbox/public endpoints.
- No interface changes required.

### Minimum viable paid plan

- **Split (Option 2):** Twelve Data Grow $29/mo for XAU/USD; crypto is free.
- **Unified (Option 1):** Twelve Data Grow $29/mo (marginal for Profile B) or Pro $99/mo (comfortable).

### Questions requiring vendor confirmation

1. Twelve Data: What are the exact data-retention limits for paid tiers? Can OHLCV be stored in PostgreSQL indefinitely?
2. Twelve Data: Is XAU/USD data available 24/7 or only during weekday trading hours? What is served on weekends?
3. Binance/Bybit: What are the data-use rights for public market data stored in a database?
4. All: Is displaying prices in a Telegram Mini App classified as "display" or "redistribution"?

---

## 14. Owner Approval Gate

> **This recommendation is advisory only. No provider has been selected or implemented.**
> The owner must explicitly choose one of the following before any implementation begins:

- **APPROVE OPTION 1** — Single unified provider (Twelve Data)
- **APPROVE OPTION 2** — Split: crypto exchange + XAU/USD provider (Bybit/Binance + Twelve Data)
- **APPROVE OPTION 3** — Primary + fallback (not recommended for initial launch)
- **REQUEST MORE RESEARCH** — Additional vendors, deeper legal review, or empirical validation
- **REJECT ALL OPTIONS** — None of the proposed architectures are acceptable

**If the owner does not respond, the result is STOPPED / BLOCKED. No implementation will proceed.**

---

## 15. Implementation Outline (For Reference Only — NOT Authorized)

### Option 1 — Twelve Data Unified

1. Create `TwelveDataAdapter` implementing `QuoteProvider` + `HistoricalCandleProvider`.
2. Map symbols: `BTC/USDT`, `ETH/USDT`, `XAU/USD`.
3. Alembic migration: seed `provider_instrument_mappings` with `provider_key='twelvedata'`.
4. Worker: replace `FakeProvider` with `TwelveDataAdapter`; update target loader SQL filter.
5. Config: `TWELVEDATA_API_KEY` env var; `quote_source_label` / `quote_venue_label` updates.
6. Tests: mock HTTP responses matching Twelve Data JSON schema; verify NormalizedQuote/NormalizedCandle validation.
7. Validate freshness policy: crypto 60s/300s, reference 300s/900s (already correct).

### Option 2 — Split (Bybit + Twelve Data)

1. Create `BybitAdapter` (crypto) and `TwelveDataAdapter` (XAU only).
2. Map: Bybit `BTCUSDT`/`ETHUSDT`; Twelve Data `XAU/USD`.
3. Alembic migration: seed mappings with `provider_key='bybit'` and `provider_key='twelvedata'`.
4. Worker: provider routing by `provider_key`; quote refresh loads correct provider per instrument.
5. Config: `TWELVEDATA_API_KEY` env var; Bybit is keyless.
6. Tests: per-adapter mock tests; cross-provider provenance verification.
7. Provenance: crypto quotes labeled "Bybit"; XAU quotes labeled "Twelve Data".

### No-implementation statement

**No code changes have been made.** This document is research and analysis only.
The active providers remain `FakeQuoteProvider` and `FakeHistoricalCandleProvider`.
The data mode remains DEMO. No provider has been selected.
