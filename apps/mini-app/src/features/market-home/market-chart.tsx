import { useMemo } from "react";

import type { Candle } from "@/shared/api/market";
import { decimalScale, decimalToScaled } from "@/shared/lib/decimal";

interface MarketChartProps {
  candles: Candle[];
}

export function MarketChart({ candles }: MarketChartProps) {
  const geometry = useMemo(() => {
    if (candles.length === 0) return null;
    const scale = candles.reduce(
      (maximum, candle) => Math.max(maximum, decimalScale(candle.close)),
      0,
    );
    const values = candles.map((candle) => decimalToScaled(candle.close, scale));
    const low = values.reduce((current, value) => value < current ? value : current);
    const high = values.reduce((current, value) => value > current ? value : current);
    const range = high - low || 1n;
    const pointList = values.map((value, index) => {
      const x = 10 + (index / Math.max(values.length - 1, 1)) * 300;
      const y = 126 - Number(((value - low) * 10000n) / range) / 10000 * 102;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    });
    const points = pointList.join(" ");
    const firstPoint = pointList[0] ?? "10,126";
    const lastPoint = pointList[pointList.length - 1] ?? "310,126";
    return {
      points,
      fillPoints: `${firstPoint.split(",")[0]},136 ${points} ${lastPoint.split(",")[0]},136`,
    };
  }, [candles]);

  if (!geometry) {
    return (
      <div className="chart-empty" role="status">
        <svg viewBox="0 0 64 44" aria-hidden="true">
          <path d="M5 34 17 24l9 5 13-18 9 8 11-12" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
        </svg>
        <p>История свечей пока недоступна</p>
      </div>
    );
  }

  return (
    <svg
      viewBox="0 0 320 140"
      role="img"
      aria-label={`График из ${candles.length} закрытых свечей`}
      className="market-chart"
      preserveAspectRatio="none"
    >
      {[28, 62, 96, 130].map((y) => (
        <line key={y} x1="8" x2="312" y1={y} y2={y} className="market-chart-grid" />
      ))}
      <polygon points={geometry.fillPoints} className="market-chart-area" />
      <polyline points={geometry.points} className="market-chart-line" />
    </svg>
  );
}
