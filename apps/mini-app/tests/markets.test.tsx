import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { decimalToScaled, Markets } from "../src/pages/markets";

const api = vi.hoisted(() => ({ getAssets: vi.fn(), getQuote: vi.fn(), getCandles: vi.fn() }));
vi.mock("../src/shared/api/market", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/shared/api/market")>()),
  ...api,
}));
vi.mock("../src/shared/telegram", () => ({ useTelegramAuth: () => ({ state: "valid" }) }));

const asset = { id: "00000000-0000-4000-8000-000000000001", slug: "btc-usdt", symbol: "BTC/USDT", display_name: "Bitcoin", asset_class: "crypto", market_type: "spot", base_asset: "BTC", quote_asset: "USDT", price_precision: 2, quantity_precision: 8, timezone: "UTC", calendar_kind: "continuous", trading_calendar: "24x7", metadata_version: 1, is_enabled: true };
const quote = { slug: "btc-usdt", price: "12345678901234567890.123456789", bid: null, ask: null, mid: null, market_status: "open", data_status: "fresh", observed_at: "2026-01-01T00:00:00Z", received_at: "2026-01-01T00:00:00Z", age_seconds: 1, stale_after_seconds: 60, provenance: { source_label: "fixture", venue_label: null, market_type: "spot", price_type: "last", delay_class: "realtime" } };
const candle = { open_time: "2026-01-01T00:00:00Z", close_time: "2026-01-01T00:01:00Z", open: "1.000000000001", high: "3.000000000001", low: "0.500000000001", close: "2.000000000001", source_label: "fixture", venue_label: null, received_at: "2026-01-01T00:01:00Z" };

function renderMarkets() { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><Markets /></QueryClientProvider>); }

describe("market screen", () => {
  it("preserves decimal differences beyond twelve fractional places", () => {
    expect(decimalToScaled("1.0000000000001", 13)).not.toBe(decimalToScaled("1.0000000000002", 13));
    expect(decimalToScaled("-1.2", 13)).toBe(-12000000000000n);
  });

  it("renders catalog, quote provenance, chart, and all supported timeframes", async () => {
    api.getAssets.mockResolvedValue({ items: [asset], next_cursor: null });
    api.getQuote.mockResolvedValue({ items: [quote], unavailable: [], not_found: [] });
    api.getCandles.mockResolvedValue({ timeframe: "1h", items: [candle] });
    renderMarkets();
    expect(await screen.findByRole("combobox", { name: "Выбор инструмента" })).toHaveValue("btc-usdt");
    expect(await screen.findByText(quote.price)).toBeInTheDocument();
    expect(screen.getByText(/Источник: fixture/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /График из 1 закрытых свечей/ })).toBeInTheDocument();
    ["1m", "5m", "15m", "1h", "4h", "1d"].forEach((timeframe) => expect(screen.getByRole("button", { name: timeframe })).toBeInTheDocument());
  });

  it("requests new candle data when the instrument or timeframe changes", async () => {
    const eth = { ...asset, id: "00000000-0000-4000-8000-000000000002", slug: "eth-usdt", symbol: "ETH/USDT", display_name: "Ethereum" };
    api.getAssets.mockResolvedValue({ items: [asset, eth], next_cursor: null });
    api.getQuote.mockImplementation((slug: string) => Promise.resolve({ items: [{ ...quote, slug }], unavailable: [], not_found: [] }));
    api.getCandles.mockResolvedValue({ timeframe: "1h", items: [candle] });
    renderMarkets();
    const select = await screen.findByRole("combobox", { name: "Выбор инструмента" });
    fireEvent.change(select, { target: { value: "eth-usdt" } });
    fireEvent.click(screen.getByRole("button", { name: "5m" }));
    await waitFor(() => expect(api.getCandles).toHaveBeenLastCalledWith("eth-usdt", "5m"));
  });

  it("renders unavailable and not-found quote classifications", async () => {
    api.getAssets.mockResolvedValue({ items: [asset], next_cursor: null });
    api.getCandles.mockResolvedValue({ timeframe: "1h", items: [] });
    api.getQuote.mockResolvedValue({ items: [], unavailable: ["btc-usdt"], not_found: [] });
    const view = renderMarkets();
    expect(await screen.findByText("Котировка временно недоступна")).toBeInTheDocument();
    view.unmount();
    api.getQuote.mockResolvedValue({ items: [], unavailable: [], not_found: ["btc-usdt"] });
    renderMarkets();
    expect(await screen.findByText("Инструмент не найден")).toBeInTheDocument();
  });
});
