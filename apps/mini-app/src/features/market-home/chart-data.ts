import type { Candle } from "@/shared/api/market";
import { decimalScale, decimalToScaled } from "@/shared/lib/decimal";

const CHART_LEFT = 10;
const CHART_RIGHT = 310;
const CHART_TOP = 20;
const CHART_BOTTOM = 120;
const CHART_CENTER = (CHART_TOP + CHART_BOTTOM) / 2;
const RATIO_SCALE = 1_000_000n;

export interface ChartPoint {
  x: number;
  y: number;
}

export interface ChartSegment {
  points: ChartPoint[];
}

export interface ChartGeometry {
  candles: Candle[];
  segments: ChartSegment[];
}

export function normalizeCandles(candles: Candle[]): Candle[] {
  const byOpenTime = new Map<string, Candle>();
  for (const candle of candles) {
    const current = byOpenTime.get(candle.open_time);
    if (!current || Date.parse(candle.received_at) >= Date.parse(current.received_at)) {
      byOpenTime.set(candle.open_time, candle);
    }
  }
  return [...byOpenTime.values()].sort(
    (left, right) => Date.parse(left.open_time) - Date.parse(right.open_time),
  );
}

export function buildChartGeometry(input: Candle[]): ChartGeometry | null {
  const candles = normalizeCandles(input);
  if (candles.length === 0) return null;

  const scale = candles.reduce(
    (maximum, candle) => Math.max(maximum, decimalScale(candle.close)),
    0,
  );
  const values = candles.map((candle) => decimalToScaled(candle.close, scale));
  const low = values.reduce((current, value) => value < current ? value : current);
  const high = values.reduce((current, value) => value > current ? value : current);
  const range = high - low;
  const points = values.map((value, index): ChartPoint => {
    const x = CHART_LEFT
      + (index / Math.max(values.length - 1, 1)) * (CHART_RIGHT - CHART_LEFT);
    const y = range === 0n
      ? CHART_CENTER
      : CHART_BOTTOM
        - Number(((value - low) * RATIO_SCALE) / range)
          / Number(RATIO_SCALE)
          * (CHART_BOTTOM - CHART_TOP);
    return { x, y };
  });

  const segments: ChartSegment[] = [];
  let current: ChartPoint[] = [];
  candles.forEach((candle, index) => {
    const previous = candles[index - 1];
    if (previous && candle.open_time !== previous.close_time) {
      segments.push({ points: current });
      current = [];
    }
    current.push(points[index]!);
  });
  if (current.length > 0) segments.push({ points: current });

  return { candles, segments };
}

export function serializePoints(points: ChartPoint[]): string {
  return points.map(({ x, y }) => `${x.toFixed(3)},${y.toFixed(3)}`).join(" ");
}
