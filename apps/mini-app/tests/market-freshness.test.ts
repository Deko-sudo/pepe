import { describe, expect, it } from "vitest";

import { quoteFreshness } from "../src/features/market-home/freshness";
import type { Quote } from "../src/shared/api/market";

const quote = {
  data_status: "fresh",
  age_seconds: 1,
} as Quote;

describe("quote freshness", () => {
  it("advances the server snapshot age with elapsed client time", () => {
    expect(quoteFreshness(quote, 0)).toEqual({ text: "только что", stale: false });
    expect(quoteFreshness(quote, 10)).toEqual({ text: "11 сек назад", stale: false });
  });

  it("marks an unrefreshed quote stale after the polling window", () => {
    expect(quoteFreshness(quote, 60)).toEqual({ text: "1 мин назад", stale: true });
  });

  it("preserves an explicit stale status from the API", () => {
    expect(quoteFreshness({ ...quote, data_status: "stale" }, 0)).toEqual({
      text: "данные устарели",
      stale: true,
    });
  });
});
