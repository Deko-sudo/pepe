import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "../src/pages/dashboard";
import { useModalStore } from "../src/shared/lib/store";

const api = vi.hoisted(() => ({
  getAssets: vi.fn(),
  getCandles: vi.fn(),
  getMarketDataCapabilities: vi.fn(),
  getQuotes: vi.fn(),
}));

vi.mock("../src/shared/telegram", () => ({
  useTelegramAuth: () => ({ state: "valid" }),
}));

vi.mock("../src/shared/api/market", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/shared/api/market")>()),
  ...api,
}));

function renderDashboard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter><Dashboard /></MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useModalStore.setState({ aiSupportOpen: false });
  api.getMarketDataCapabilities.mockResolvedValue({
    contract_version: "v1",
    mode: "demo",
    status: "available",
    numeric_quotes_available: true,
    server_candles_available: true,
    embedded_chart_available: false,
    analytics_available: false,
    quote_cards_visible: true,
    unavailable_reason_code: null,
  });
  api.getAssets.mockResolvedValue({
    items: [{
      id: "00000000-0000-4000-8000-000000000001", slug: "btc-usdt", symbol: "BTC/USDT", display_name: "Bitcoin",
      asset_class: "crypto", market_type: "spot", base_asset: "BTC", quote_asset: "USDT", price_precision: 2,
      quantity_precision: 8, timezone: "UTC", calendar_kind: "continuous", trading_calendar: "24x7",
      metadata_version: 1, is_enabled: true,
    }],
    next_cursor: null,
  });
  api.getQuotes.mockResolvedValue({
    items: [{
      slug: "btc-usdt", price: "119000.00", bid: null, ask: null, mid: null, market_status: "open",
      data_status: "fresh", observed_at: "2026-07-28T05:00:00Z", received_at: "2026-07-28T05:00:01Z", age_seconds: 1, stale_after_seconds: 60,
      provenance: { source_label: "Synthetic test source", venue_label: null, market_type: "spot", price_type: "last", delay_class: "demo" },
    }],
    unavailable: [],
    not_found: [],
  });
  api.getCandles.mockResolvedValue({ timeframe: "1h", items: [] });
});

describe("AI Support Modal", () => {
  it("opens modal from the neutral Stage 8 presentation card", async () => {
    renderDashboard();
    fireEvent.click(await screen.findByRole("button", { name: "Открыть AI-поддержку" }));
    expect(screen.getByRole("dialog", { name: "AI-поддержка · Beta" })).toBeInTheDocument();
    expect(screen.getByText(/Раздел находится в разработке/)).toBeInTheDocument();
  });

  it("moves focus into the modal and restores it after closing", async () => {
    renderDashboard();
    await screen.findAllByText("119 000");
    const trigger = screen.getByRole("button", { name: "Открыть AI-поддержку" });
    trigger.focus();
    expect(trigger).toHaveFocus();
    fireEvent.click(trigger);
    await waitFor(() => expect(screen.getByText("Понятно")).toHaveFocus());
    fireEvent.click(screen.getByText("Понятно"));
    expect(screen.queryByText(/Раздел находится в разработке/)).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Открыть AI-поддержку" })).toHaveFocus());
  });
});
