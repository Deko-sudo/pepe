import { afterEach, describe, expect, it, vi } from "vitest";

import { activateSessionToken, clearSessionToken } from "../src/shared/api";
import { CandleSchema, getEmbeddedChartConfiguration, getQuotes, QuoteSchema, type Timeframe } from "../src/shared/api/market";

const quote = {
  slug: "btc-usdt",
  price: "100.00",
  bid: null,
  ask: null,
  mid: null,
  open_24h: null,
  high_24h: null,
  low_24h: null,
  change_24h: null,
  change_percent_24h: null,
  base_volume_24h: null,
  quote_volume_24h: null,
  market_status: "open",
  data_status: "fresh",
  observed_at: "2026-01-01T00:00:00Z",
  received_at: "2026-01-01T00:00:00Z",
  age_seconds: 1,
  stale_after_seconds: 60,
  provenance: {
    source_label: "Synthetic test source",
    venue_label: null,
    market_type: "spot",
    price_type: "last",
    delay_class: "realtime",
  },
};

const embeddedConfiguration = (slug: string, timeframe: Timeframe) => ({
  version: 1,
  mode: "embedded",
  provider: "tradingview_isolated_wrapper",
  asset: slug,
  timeframe,
  wrapper_origin: "http://127.0.0.1:4173",
  wrapper_path: `/chart/${slug}/${timeframe}`,
  wrapper_url: `http://127.0.0.1:4173/chart/${slug}/${timeframe}`,
});

afterEach(() => {
  clearSessionToken();
  vi.restoreAllMocks();
});

describe("market API client", () => {
  it("explicitly models factual 24-hour quote and candle metadata", () => {
    expect(Object.keys(QuoteSchema.shape)).toEqual(expect.arrayContaining([
      "open_24h", "high_24h", "low_24h", "change_24h", "change_percent_24h", "base_volume_24h", "quote_volume_24h",
    ]));
    expect(Object.keys(CandleSchema.shape)).toEqual(expect.arrayContaining(["base_volume", "quote_volume", "trade_count"]));
  });

  it.each(["", ".5", "1e3", "123.", "not-a-number"])(
    "rejects non-canonical decimal payload %j at the schema boundary",
    (value) => {
      expect(QuoteSchema.safeParse({ ...quote, price: value }).success).toBe(false);
      expect(CandleSchema.safeParse({
        open_time: "2026-01-01T00:00:00Z",
        close_time: "2026-01-01T01:00:00Z",
        open: value,
        high: "2",
        low: "1",
        close: "1.5",
        base_volume: null,
        quote_volume: null,
        trade_count: null,
        source_label: "Synthetic test source",
        venue_label: null,
        received_at: "2026-01-01T01:00:00Z",
      }).success).toBe(false);
    },
  );

  it("requests a credentialed quote batch with repeated slug parameters", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ items: [quote], unavailable: [], not_found: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    await getQuotes(["btc-usdt", "eth-usdt", "xau-usd"]);

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/assets/quotes?slug=btc-usdt&slug=eth-usdt&slug=xau-usd",
      { credentials: "include" },
    );
  });

  it("adds the in-memory header session to market requests", async () => {
    activateSessionToken("desktop-session-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ items: [quote], unavailable: [], not_found: [] }), {
        status: 200,
      }),
    );

    await getQuotes(["btc-usdt"]);

    expect(fetchSpy.mock.calls[0][0]).toBe("/api/v1/assets/quotes?slug=btc-usdt");
    expect(fetchSpy.mock.calls[0][1]).toEqual(expect.objectContaining({ credentials: "include" }));
    const headers = new Headers(fetchSpy.mock.calls[0][1]?.headers);
    expect(headers.get("Authorization")).toContain("desktop-session-token");
  });

  it.each(
    ["btc-usdt", "eth-usdt", "xau-usd"].flatMap((slug) =>
      (["1m", "5m", "15m", "1h", "4h", "1d"] as Timeframe[]).map((timeframe) => [slug, timeframe] as const),
    ),
  )("requests the exact authenticated W3 configuration route for %s %s", async (slug, timeframe) => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(embeddedConfiguration(slug, timeframe)), { status: 200 }));

    await getEmbeddedChartConfiguration(slug, timeframe);

    expect(fetchSpy.mock.calls[0][0]).toBe(`/api/v1/market-data/embedded-chart-config?slug=${slug}&timeframe=${timeframe}`);
    expect(fetchSpy.mock.calls[0][1]).toEqual(expect.objectContaining({ credentials: "include" }));
  });

  it("passes caller cancellation through to the authenticated configuration request", async () => {
    const controller = new AbortController();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(embeddedConfiguration("btc-usdt", "1h")), { status: 200 }));

    await getEmbeddedChartConfiguration("btc-usdt", "1h", controller.signal);

    expect(fetchSpy.mock.calls[0][1]).toEqual(expect.objectContaining({ signal: controller.signal, credentials: "include" }));
  });

  it("preserves an intentional AbortError rather than converting it to an API error", async () => {
    const controller = new AbortController();
    controller.abort();
    const abortError = new DOMException("The operation was aborted", "AbortError");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(abortError);

    await expect(getEmbeddedChartConfiguration("btc-usdt", "1h", controller.signal)).rejects.toBe(abortError);
  });
});
