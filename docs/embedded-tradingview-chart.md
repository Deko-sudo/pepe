# TradingView embedded chart (PR B)

PR B is display-only and disabled by default. It is available only when all three settings are explicitly set: `MARKET_DATA_MODE=embedded`, `EMBEDDED_CHART_PROVIDER=tradingview`, and `EMBEDDED_CHART_ENABLED=true`.

The integration uses TradingView's official Advanced Chart iframe endpoint, not TradingView JavaScript in Pepe's origin. The iframe receives no Pepe authentication or Telegram data. Pepe neither retrieves nor stores raw quote/candle data from the frame.

## Allowlisted mappings

| Pepe slug | TradingView symbol | source semantics |
| --- | --- | --- |
| `btc-usdt` | `BINANCE:BTCUSDT` | Binance BTC/USDT spot (exchange-specific) |
| `eth-usdt` | `BINANCE:ETHUSDT` | Binance ETH/USDT spot (exchange-specific) |
| `xau-usd` | `OANDA:XAUUSD` | OANDA gold spot / USD reference |

All mappings permit `1m`, `5m`, `15m`, `1h`, `4h`, and `1d`. The UI keeps TradingView attribution visible and offers only a user-initiated allowlisted TradingView fallback link. Delay status is provider/venue-dependent and is not asserted by Pepe.

The Mini App CSP permits framing only `https://www.tradingview-widget.com`; no TradingView script or top-level `connect-src` exception is added. Production activation requires owner physical-device testing. Regional availability is not guaranteed for the Russian Federation or DPR.
