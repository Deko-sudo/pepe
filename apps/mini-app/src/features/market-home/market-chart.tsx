import { useMemo } from "react";

import type { Candle } from "@/shared/api/market";

import { buildChartGeometry, serializePoints } from "./chart-data";

interface MarketChartProps {
  candles: Candle[];
}

export function MarketChart({ candles }: MarketChartProps) {
  const geometry = useMemo(() => buildChartGeometry(candles), [candles]);

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
      aria-label={`График из ${geometry.candles.length} закрытых свечей`}
      className="market-chart"
      preserveAspectRatio="none"
    >
      {[28, 62, 96, 130].map((y) => (
        <line key={y} x1="8" x2="312" y1={y} y2={y} className="market-chart-grid" />
      ))}
      {geometry.segments.map((segment, index) => {
        const points = serializePoints(segment.points);
        const first = segment.points[0];
        const last = segment.points[segment.points.length - 1];
        if (!first || !last) return null;
        if (segment.points.length === 1) {
          return <circle key={`point-${index}`} cx={first.x} cy={first.y} r="2.5" className="market-chart-point" />;
        }
        return (
          <g key={`segment-${index}`}>
            <polygon
              points={`${first.x.toFixed(3)},130 ${points} ${last.x.toFixed(3)},130`}
              className="market-chart-area"
            />
            <polyline points={points} className="market-chart-line" />
          </g>
        );
      })}
    </svg>
  );
}
