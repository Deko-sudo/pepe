# Embedded chart delivery foundation (PR B)

No chart provider is selected or implemented. Embedded charts are disabled by default: `EMBEDDED_CHART_ENABLED=false` and `EMBEDDED_CHART_PROVIDER=none`.

The authenticated market capability contract is authoritative. In `embedded` mode, numeric quotes, server candles, quote cards, and embedded content are unavailable. The capability reason is `embedded_chart_provider_not_configured`; the embedded-config endpoint validates only canonical Pepe slugs (`btc-usdt`, `eth-usdt`, `xau-usd`) and timeframes (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`) before returning private, no-store HTTP 409.

The Mini App preserves asset and timeframe selection and renders an accessible provider-not-configured state. It loads no external content, script, fallback URL, or synthetic market values in embedded mode. PR A quote/candle fail-closed behavior remains active.

A future provider needs explicit owner approval for official embedding support, public-display rights, regional availability, instrument equivalence, narrow CSP allowlisting, and Telegram Android/Desktop testing. Any provider-specific iframe, script, domain, wrapper, fallback, credential, raw-data processing, or Stage 9 behavior remains out of scope.
