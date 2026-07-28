import { describe, expect, it } from "vitest";

import {
  candleStatistics,
  decimalToScaled,
  formatDecimal,
  formatSignedDecimal,
} from "../src/shared/lib/decimal";

const candles = [
  {
    open_time: "2026-01-01T00:00:00Z",
    close_time: "2026-01-01T01:00:00Z",
    open: "100.100000000001",
    high: "110.200000000001",
    low: "95.050000000001",
    close: "105.100000000001",
    base_volume: null,
    quote_volume: null,
    trade_count: null,
    source_label: "Synthetic historical candle source",
    venue_label: null,
    received_at: "2026-01-01T01:00:00Z",
  },
  {
    open_time: "2026-01-01T01:00:00Z",
    close_time: "2026-01-01T02:00:00Z",
    open: "105.100000000001",
    high: "120.300000000001",
    low: "101.100000000001",
    close: "115.300000000001",
    base_volume: null,
    quote_volume: null,
    trade_count: null,
    source_label: "Synthetic historical candle source",
    venue_label: null,
    received_at: "2026-01-01T02:00:00Z",
  },
];

describe("precision-safe decimal presentation", () => {
  it("preserves differences beyond twelve fractional places", () => {
    expect(decimalToScaled("1.0000000000001", 13)).not.toBe(
      decimalToScaled("1.0000000000002", 13),
    );
    expect(decimalToScaled("-1.2", 13)).toBe(-12000000000000n);
  });

  it("formats decimal strings without converting them to floating point", () => {
    expect(formatDecimal("12345678901234567890.1200", 4)).toBe(
      "12 345 678 901 234 567 890.12",
    );
  });

  it("formats signed decimal changes without floating-point conversion", () => {
    expect(formatSignedDecimal("1.6900", 2)).toBe("+1.69");
    expect(formatSignedDecimal("-0.2500", 2)).toBe("−0.25");
    expect(formatSignedDecimal("0.0000", 2)).toBe("0");
  });

  it("derives high, low, average close, and range from candle decimals", () => {
    expect(candleStatistics(candles)).toEqual({
      high: "120.300000000001",
      low: "95.050000000001",
      average: "110.200000000001",
      range: "25.250000000000",
    });
  });
});
