export const WRAPPER_ORIGIN = "http://127.0.0.1:4173";
export const HARNESS_ORIGIN = "http://127.0.0.1:4174";
export const SCRIPT_URL = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
export const FRAME_TIMEOUT_MS = 12_000;

export const routes = Object.freeze({
  "btc-usdt": Object.freeze({
    symbol: "BINANCE:BTCUSDT",
    semantics: "Binance BTC/USDT spot market. Delay unknown.",
    source: "TradingView chart source: Binance.",
  }),
  "eth-usdt": Object.freeze({
    symbol: "BINANCE:ETHUSDT",
    semantics: "Binance ETH/USDT spot market. Delay unknown.",
    source: "TradingView chart source: Binance.",
  }),
  "xau-usd": Object.freeze({
    symbol: "OANDA:XAUUSD",
    semantics: "OANDA XAU/USD broker/reference-style quote. Not exchange-traded spot. Delay unknown.",
    source: "TradingView chart source: OANDA. Final XAU/USD product acceptance remains an owner production gate.",
  }),
});

export const intervals = Object.freeze({
  "1m": "1",
  "5m": "5",
  "15m": "15",
  "1h": "60",
  "4h": "240",
  "1d": "D",
});

export const lifecycleEvents = Object.freeze([
  "wrapper-document-ready",
  "provider-script-load-failed",
  "provider-frame-created",
  "provider-frame-document-loaded",
  "provider-frame-timeout",
  "wrapper-configuration-invalid",
]);

export function isCanonicalRoute(slug, timeframe) {
  return Object.hasOwn(routes, slug) && Object.hasOwn(intervals, timeframe);
}

export function canonicalPath(slug, timeframe) {
  return `/chart/${slug}/${timeframe}`;
}

export function routeConfig(slug, timeframe) {
  if (!isCanonicalRoute(slug, timeframe)) return null;
  return Object.freeze({ slug, timeframe, ...routes[slug], interval: intervals[timeframe] });
}

export function parseCanonicalUrl(value) {
  const url = new URL(value, WRAPPER_ORIGIN);
  if (url.origin !== WRAPPER_ORIGIN) return null;
  if (url.search || url.hash) return null;
  const match = /^\/chart\/(btc-usdt|eth-usdt|xau-usd)\/(1m|5m|15m|1h|4h|1d)$/.exec(url.pathname);
  return match ? routeConfig(match[1], match[2]) : null;
}
