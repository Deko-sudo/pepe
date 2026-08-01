import { describe, expect, it } from "vitest";
import { validateEmbeddedChartConfiguration } from "@/shared/api/market";

const config = {
  version: 1,
  mode: "embedded",
  provider: "tradingview_isolated_wrapper",
  asset: "btc-usdt",
  timeframe: "1h",
  wrapper_origin: "http://127.0.0.1:4173",
  wrapper_path: "/chart/btc-usdt/1h",
  wrapper_url: "http://127.0.0.1:4173/chart/btc-usdt/1h",
};
const parentOrigin = "http://localhost:5173";
const validate = (value: unknown) => validateEmbeddedChartConfiguration(value, "btc-usdt", "1h", parentOrigin);

describe("W3 embedded wrapper configuration", () => {
  it("accepts the exact canonical configuration without reconstructing its URL", () => {
    expect(validate(config)).toEqual(config);
  });

  it.each([
    ["contract version", { ...config, version: 2 }],
    ["mode", { ...config, mode: "live" }],
    ["provider", { ...config, provider: "none" }],
    ["asset", { ...config, asset: "eth-usdt" }],
    ["timeframe", { ...config, timeframe: "5m" }],
    ["requested route", { ...config, wrapper_path: "/chart/eth-usdt/1h" }],
    ["URL origin", { ...config, wrapper_url: "http://other.local/chart/btc-usdt/1h" }],
    ["URL path", { ...config, wrapper_url: "http://127.0.0.1:4173/chart/btc-usdt/5m" }],
    ["same origin", { ...config, wrapper_origin: parentOrigin, wrapper_url: `${parentOrigin}/chart/btc-usdt/1h` }],
    ["relative origin", { ...config, wrapper_origin: "/wrapper" }],
    ["relative URL", { ...config, wrapper_url: "/chart/btc-usdt/1h" }],
    ["protocol-relative URL", { ...config, wrapper_url: "//127.0.0.1:4173/chart/btc-usdt/1h" }],
    ["origin credentials", { ...config, wrapper_origin: "http://user:pass@127.0.0.1:4173" }],
    ["URL credentials", { ...config, wrapper_url: "http://user:pass@127.0.0.1:4173/chart/btc-usdt/1h" }],
    ["origin query", { ...config, wrapper_origin: "http://127.0.0.1:4173?token=x" }],
    ["URL query", { ...config, wrapper_url: "http://127.0.0.1:4173/chart/btc-usdt/1h?telegram=x" }],
    ["origin fragment", { ...config, wrapper_origin: "http://127.0.0.1:4173#session" }],
    ["URL fragment", { ...config, wrapper_url: "http://127.0.0.1:4173/chart/btc-usdt/1h#user" }],
    ["malformed URL", { ...config, wrapper_url: "https://[" }],
    ["direct TradingView", { ...config, wrapper_origin: "https://tradingview.com", wrapper_url: "https://tradingview.com/chart/btc-usdt/1h" }],
    ["TradingView subdomain", { ...config, wrapper_origin: "https://s.tradingview.com", wrapper_url: "https://s.tradingview.com/chart/btc-usdt/1h" }],
    ["unknown security field", { ...config, session: "[REDACTED]" }],
  ])("rejects unsafe %s", (_, value) => expect(() => validate(value)).toThrow());

  it.each(["version", "mode", "provider", "asset", "timeframe", "wrapper_origin", "wrapper_path", "wrapper_url"])("rejects missing %s", (field) => {
    const value = { ...config } as Record<string, unknown>;
    delete value[field];
    expect(() => validate(value)).toThrow();
  });
});
