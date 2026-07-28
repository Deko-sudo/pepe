import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarketChart } from "../src/features/market-home/market-chart";
import type { Candle } from "../src/shared/api/market";

function candle(openTime: string, closeTime: string, close: string): Candle {
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
  };
}

describe("MarketChart", () => {
  it("renders an accessible empty state", () => {
    const { container } = render(<MarketChart candles={[]} />);

    expect(screen.getByRole("status")).toHaveTextContent("История свечей пока недоступна");
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("renders a single candle as a centered point", () => {
    const { container } = render(
      <MarketChart
        candles={[candle("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "100.00")]}
      />,
    );

    expect(screen.getByRole("img", { name: "График из 1 закрытых свечей" })).toBeInTheDocument();
    expect(container.querySelector("circle.market-chart-point")).toHaveAttribute("cy", "70");
    expect(container.querySelector("polyline.market-chart-line")).not.toBeInTheDocument();
  });

  it("does not connect genuine gaps", () => {
    const { container } = render(
      <MarketChart
        candles={[
          candle("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "100.00"),
          candle("2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z", "101.00"),
          candle("2026-01-01T03:00:00Z", "2026-01-01T04:00:00Z", "102.00"),
        ]}
      />,
    );

    expect(container.querySelectorAll("polyline.market-chart-line")).toHaveLength(1);
    expect(container.querySelectorAll("circle.market-chart-point")).toHaveLength(1);
  });
});
