import { routeConfig } from "./config.mjs";
for (const [slug, timeframe, symbol, interval] of [
  ["btc-usdt", "1m", "BINANCE:BTCUSDT", "1"],
  ["eth-usdt", "4h", "BINANCE:ETHUSDT", "240"],
  ["xau-usd", "1d", "OANDA:XAUUSD", "D"],
]) {
  const config = routeConfig(slug, timeframe);
  if (!config || config.symbol !== symbol || config.interval !== interval) throw new Error("Route mapping type contract failed");
}
console.log("Static mapping type contract checks passed.");
