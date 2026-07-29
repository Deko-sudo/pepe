import { describe, expect, it } from "vitest";

import { quoteFreshness } from "../src/features/market-home/freshness";
import type { Quote } from "../src/shared/api/market";

const baseQuote = {
  slug: "btc-usdt",
  price: "119000.00",
  data_status: "fresh",
  age_seconds: 1,
  stale_after_seconds: 60,
} as Quote;

function quoteWith(overrides: Partial<Quote>): Quote {
  return { ...baseQuote, ...overrides } as Quote;
}

describe("quote freshness", () => {
  it("advances the server snapshot age with elapsed client time", () => {
    expect(quoteFreshness(baseQuote, 0)).toEqual({ text: "только что", stale: false });
    expect(quoteFreshness(baseQuote, 10)).toEqual({ text: "11 сек назад", stale: false });
  });

  it("marks a crypto quote stale at its configured 60-second threshold", () => {
    const crypto = quoteWith({ stale_after_seconds: 60, age_seconds: 0 });
    expect(quoteFreshness(crypto, 59)).toHaveProperty("stale", false);
    expect(quoteFreshness(crypto, 60)).toHaveProperty("stale", true);
  });

  it("keeps XAU/USD fresh between 60 seconds and its 300-second reference threshold", () => {
    const xau = quoteWith({ slug: "xau-usd", stale_after_seconds: 300, age_seconds: 0 });
    expect(quoteFreshness(xau, 90)).toHaveProperty("stale", false);
    expect(quoteFreshness(xau, 200)).toHaveProperty("stale", false);
  });

  it("marks XAU/USD stale at its configured reference threshold", () => {
    const xau = quoteWith({ slug: "xau-usd", stale_after_seconds: 300, age_seconds: 0 });
    expect(quoteFreshness(xau, 299)).toHaveProperty("stale", false);
    expect(quoteFreshness(xau, 300)).toHaveProperty("stale", true);
  });

  it("preserves an explicit stale status from the server immediately", () => {
    expect(quoteFreshness(quoteWith({ data_status: "stale" }), 0)).toEqual({
      text: "данные устарели",
      stale: true,
    });
  });

  it("advances the effective age after the response snapshot", () => {
    const snapshot = quoteWith({ age_seconds: 40, stale_after_seconds: 60 });
    expect(quoteFreshness(snapshot, 0)).toHaveProperty("stale", false);
    expect(quoteFreshness(snapshot, 20)).toHaveProperty("stale", true);
  });

  it("does not leave old data fresh indefinitely after a failed refresh", () => {
    const stale = quoteWith({ age_seconds: 50, stale_after_seconds: 60 });
    expect(quoteFreshness(stale, 10)).toHaveProperty("stale", true);
    expect(quoteFreshness(stale, 300)).toHaveProperty("stale", true);
  });

  it("fails safely when the threshold is missing or invalid", () => {
    expect(quoteFreshness(quoteWith({ stale_after_seconds: 0 }), 600)).toHaveProperty("stale", false);
    expect(quoteFreshness(quoteWith({ stale_after_seconds: NaN }), 600)).toHaveProperty("stale", false);
    expect(quoteFreshness(quoteWith({ stale_after_seconds: -5 }), 600)).toHaveProperty("stale", false);
  });

  it("does not encode any slug-specific freshness policy", () => {
    // The threshold comes entirely from the quote payload; the same function
    // serves crypto and reference assets without branching on slug.
    const crypto = quoteWith({ slug: "btc-usdt", stale_after_seconds: 60 });
    const reference = quoteWith({ slug: "xau-usd", stale_after_seconds: 300 });
    expect(quoteFreshness(crypto, 90).stale).toBe(true);
    expect(quoteFreshness(reference, 90).stale).toBe(false);
  });
});
