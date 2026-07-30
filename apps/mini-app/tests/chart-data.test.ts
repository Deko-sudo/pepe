import { describe, expect, it } from "vitest";

import type { Candle } from "../src/shared/api/market";
import {
  buildChartGeometry,
  normalizeCandles,
} from "../src/features/market-home/chart-data";

function candle(
  openTime: string,
  closeTime: string,
  close: string,
  overrides: Partial<Candle> = {},
): Candle {
  return {
    open_time: openTime,
    close_time: closeTime,
    open: close,
    high: close,
    low: close,
    close,
    base_volume: null,
    quote_volume: null,
    trade_count: null,
    source_label: "Synthetic historical candle source",
    venue_label: null,
    received_at: closeTime,
    ...overrides,
  };
}

describe("chart candle normalization", () => {
  it("returns no geometry for an empty candle set", () => {
    expect(normalizeCandles([])).toEqual([]);
    expect(buildChartGeometry([])).toBeNull();
  });

  it("sorts chronologically and keeps only the newest duplicate identity", () => {
    const oldDuplicate = candle(
      "2026-01-01T00:00:00Z",
      "2026-01-01T01:00:00Z",
      "10",
      { received_at: "2026-01-01T01:00:01Z" },
    );
    const newDuplicate = { ...oldDuplicate, close: "11", received_at: "2026-01-01T01:00:02Z" };
    const later = candle("2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z", "12");

    expect(normalizeCandles([later, oldDuplicate, newDuplicate])).toEqual([
      newDuplicate,
      later,
    ]);
  });

  it("breaks chart segments at genuine time gaps", () => {
    const geometry = buildChartGeometry([
      candle("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "10"),
      candle("2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z", "11"),
      candle("2026-01-01T03:00:00Z", "2026-01-01T04:00:00Z", "12"),
    ]);

    expect(geometry?.segments).toHaveLength(2);
    expect(geometry?.segments.map((segment) => segment.points.length)).toEqual([2, 1]);
  });

  it("centers constant and single-candle series without invalid coordinates", () => {
    for (const candles of [
      [candle("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "100")],
      [
        candle("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "100"),
        candle("2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z", "100"),
      ],
    ]) {
      const geometry = buildChartGeometry(candles);
      expect(geometry?.segments.flatMap((segment) => segment.points).every((point) => point.y === 70)).toBe(true);
      expect(JSON.stringify(geometry)).not.toMatch(/NaN|Infinity/);
    }
  });

  it("keeps large and negative decimal coordinates finite and monotonic", () => {
    const geometry = buildChartGeometry([
      candle("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "-99999999999999999999.0000000002"),
      candle("2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z", "-99999999999999999999.0000000001"),
      candle("2026-01-01T02:00:00Z", "2026-01-01T03:00:00Z", "99999999999999999999.0000000001"),
    ]);
    const points = geometry?.segments[0]?.points ?? [];

    expect(points).toHaveLength(3);
    expect(points[0]!.x).toBeLessThan(points[1]!.x);
    expect(points[1]!.x).toBeLessThan(points[2]!.x);
    expect(points[0]!.y).toBeGreaterThanOrEqual(points[1]!.y);
    expect(points[1]!.y).toBeGreaterThan(points[2]!.y);
    expect(points.every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y))).toBe(true);
  });
});
