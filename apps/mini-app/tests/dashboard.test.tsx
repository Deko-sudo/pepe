import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "../src/pages/dashboard";

const api = vi.hoisted(() => ({
  getAssets: vi.fn(),
  getQuotes: vi.fn(),
  getCandles: vi.fn(),
}));
const auth = vi.hoisted(() => ({ state: "valid" as string }));

vi.mock("../src/shared/api/market", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/shared/api/market")>()),
  ...api,
}));
vi.mock("../src/shared/telegram", () => ({
  useTelegramAuth: () => ({ state: auth.state }),
}));

const assets = [
  { id: "00000000-0000-4000-8000-000000000001", slug: "btc-usdt", symbol: "BTC/USDT", display_name: "Bitcoin", asset_class: "crypto_spot", market_type: "spot", base_asset: "BTC", quote_asset: "USDT", price_precision: 2, quantity_precision: 8, timezone: "UTC", calendar_kind: "always_open", trading_calendar: "crypto-24x7", metadata_version: 1, is_enabled: true },
  { id: "00000000-0000-4000-8000-000000000002", slug: "eth-usdt", symbol: "ETH/USDT", display_name: "Ethereum", asset_class: "crypto_spot", market_type: "spot", base_asset: "ETH", quote_asset: "USDT", price_precision: 2, quantity_precision: 8, timezone: "UTC", calendar_kind: "always_open", trading_calendar: "crypto-24x7", metadata_version: 1, is_enabled: true },
  { id: "00000000-0000-4000-8000-000000000003", slug: "xau-usd", symbol: "XAU/USD", display_name: "Золото", asset_class: "metal_fx_spot", market_type: "spot", base_asset: "XAU", quote_asset: "USD", price_precision: 2, quantity_precision: null, timezone: "UTC", calendar_kind: "provider_session", trading_calendar: "xau-usd-provider-session", metadata_version: 1, is_enabled: true },
];

const quoteFor = (slug: string, price: string, dataStatus = "fresh") => ({
  slug,
  price,
  bid: null,
  ask: null,
  mid: null,
  open_24h: "117000.00",
  high_24h: "120000.00",
  low_24h: "110000.00",
  change_24h: "2000.00",
  change_percent_24h: "1.71",
  base_volume_24h: null,
  quote_volume_24h: null,
  market_status: "open",
  data_status: dataStatus,
  observed_at: "2026-07-28T08:00:00Z",
  received_at: "2026-07-28T08:00:01Z",
  age_seconds: 1,
  provenance: {
    source_label: "Synthetic test source",
    venue_label: null,
    market_type: "spot",
    price_type: "last",
    delay_class: "realtime",
  },
});

const candles = [
  { open_time: "2026-07-28T06:00:00Z", close_time: "2026-07-28T07:00:00Z", open: "116000.00", high: "118900.00", low: "115500.00", close: "118000.00", source_label: "Synthetic historical candle source", venue_label: null, received_at: "2026-07-28T07:00:01Z" },
  { open_time: "2026-07-28T07:00:00Z", close_time: "2026-07-28T08:00:00Z", open: "118000.00", high: "120000.00", low: "117500.00", close: "119000.00", source_label: "Synthetic historical candle source", venue_label: null, received_at: "2026-07-28T08:00:01Z" },
];

function renderDashboard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  auth.state = "valid";
  api.getAssets.mockReset().mockResolvedValue({ items: assets, next_cursor: null });
  api.getQuotes.mockReset().mockResolvedValue({
    items: [
      quoteFor("btc-usdt", "119000.00"),
      quoteFor("eth-usdt", "4200.50"),
      quoteFor("xau-usd", "2410.10"),
    ],
    unavailable: [],
    not_found: [],
  });
  api.getCandles.mockReset().mockResolvedValue({ timeframe: "1h", items: candles });
});

describe("Stage 8 home dashboard", () => {
  it("renders a real-data hero, factual context, actions, and feed", async () => {
    renderDashboard();

    expect(await screen.findByRole("heading", { name: "Pepe" })).toBeInTheDocument();
    expect((await screen.findAllByText("119 000")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("DEMO").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Открыть рынки" })).toHaveAttribute("href", "/markets");
    expect(screen.getByRole("link", { name: "Перейти к сессии" })).toHaveAttribute("href", "#session-card");
    expect(screen.getByRole("link", { name: "Как это работает" })).toHaveAttribute("href", "#ai-support");
    expect(screen.getByText("Состояние данных")).toBeInTheDocument();
    expect(screen.getByText("Рынок открыт")).toBeInTheDocument();
    expect(screen.getByText("+1.71%")).toBeInTheDocument();
    expect(screen.getByText("Макс. · 24 ч")).toBeInTheDocument();
    expect(screen.getByText("Мин. · 24 ч")).toBeInTheDocument();
    expect(screen.getByText("last · realtime")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Лента" })).toBeInTheDocument();
    expect(screen.getAllByLabelText("Bitcoin").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("Ethereum").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("Золото").length).toBeGreaterThan(0);
    expect(screen.queryByText("$118,420.50")).not.toBeInTheDocument();
  });

  it("renders all candle timeframes and precision-safe derived statistics", async () => {
    renderDashboard();

    expect(await screen.findByRole("img", { name: /График из 2 закрытых свечей/ })).toBeInTheDocument();
    ["1m", "5m", "15m", "1h", "4h", "1d"].forEach((timeframe) => {
      expect(screen.getByRole("button", { name: timeframe })).toBeInTheDocument();
    });
    expect(screen.getAllByText("120 000").length).toBeGreaterThan(0);
    expect(screen.getAllByText("115 500").length).toBeGreaterThan(0);
    expect(screen.getByText("118 500")).toBeInTheDocument();
    expect(screen.getByText("4 500")).toBeInTheDocument();
    expect(screen.getByText("Диапазон")).toBeInTheDocument();
    expect(screen.queryByText("Спред")).not.toBeInTheDocument();
  });

  it("keys candle requests by selected instrument and timeframe", async () => {
    renderDashboard();
    await screen.findAllByText("119 000");

    fireEvent.click(screen.getByRole("button", { name: "Выбрать Ethereum" }));
    fireEvent.click(screen.getByRole("button", { name: "5m" }));

    await waitFor(() => expect(api.getCandles).toHaveBeenLastCalledWith("eth-usdt", "5m"));
  });

  it("shows session, AI presentation, and no prohibited analytics", async () => {
    renderDashboard();
    await screen.findAllByText("119 000");

    expect(screen.getByRole("heading", { name: "Торговая сессия" })).toBeInTheDocument();
    expect(screen.getByText("Круглосуточный рынок")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "AI-поддержка" })).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.queryByText(/Trend Score|EMA|RSI|ATR|FVG|влияние BTC/i)).not.toBeInTheDocument();
  });

  it("renders a session-required state without issuing market requests", () => {
    auth.state = "browser";
    renderDashboard();

    expect(screen.getByRole("alert")).toHaveTextContent("Откройте Pepe через Telegram");
    expect(api.getAssets).not.toHaveBeenCalled();
    expect(api.getQuotes).not.toHaveBeenCalled();
    expect(api.getCandles).not.toHaveBeenCalled();
  });

  it("preserves unavailable, stale, and retry states", async () => {
    api.getQuotes.mockResolvedValue({
      items: [quoteFor("eth-usdt", "4200.50"), quoteFor("xau-usd", "2410.10")],
      unavailable: ["btc-usdt"],
      not_found: [],
    });
    api.getCandles.mockResolvedValue({ timeframe: "1h", items: [] });
    renderDashboard();

    expect(await screen.findByText("Котировка временно недоступна")).toBeInTheDocument();
    expect(await screen.findByText("История свечей пока недоступна")).toBeInTheDocument();

    api.getQuotes.mockResolvedValue({
      items: [quoteFor("btc-usdt", "119000.00", "stale")],
      unavailable: [],
      not_found: [],
    });
    fireEvent.click(screen.getByRole("button", { name: "Повторить загрузку" }));
    await waitFor(() => expect(api.getQuotes).toHaveBeenCalledTimes(2));
  });
});