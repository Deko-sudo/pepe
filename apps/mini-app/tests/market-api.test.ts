import { afterEach, describe, expect, it, vi } from "vitest";

import { CandleSchema, getQuotes, QuoteSchema } from "../src/shared/api/market";

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
  provenance: {
    source_label: "Synthetic test source",
    venue_label: null,
    market_type: "spot",
    price_type: "last",
    delay_class: "realtime",
  },
};

afterEach(() => {
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
});
