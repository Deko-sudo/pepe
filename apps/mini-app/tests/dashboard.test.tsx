import {
  focusManager,
  onlineManager,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "../src/pages/dashboard";
import { ApiError } from "../src/shared/api";

const api = vi.hoisted(() => ({
  getAssets: vi.fn(),
  getQuotes: vi.fn(),
  getCandles: vi.fn(),
}));
const auth = vi.hoisted(() => ({
  state: "valid" as string,
  telegramInitState: "TG_READY" as string,
  diagnosticCode: null as string | null,
}));

vi.mock("../src/shared/api/market", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/shared/api/market")>()),
  ...api,
}));
vi.mock("../src/shared/telegram", () => ({
  useTelegramAuth: () => auth,
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
  stale_after_seconds: 60,
  provenance: {
    source_label: "Synthetic test source",
    venue_label: null,
    market_type: "spot",
    price_type: "last",
    delay_class: "realtime",
  },
});

const quotesResponse = (bitcoinPrice: string) => ({
  items: [
    quoteFor("btc-usdt", bitcoinPrice),
    quoteFor("eth-usdt", "4200.50"),
    quoteFor("xau-usd", "2410.10"),
  ],
  unavailable: [] as string[],
  not_found: [] as string[],
});

const candles = [
  { open_time: "2026-07-28T06:00:00Z", close_time: "2026-07-28T07:00:00Z", open: "116000.00", high: "118900.00", low: "115500.00", close: "118000.00", source_label: "Synthetic historical candle source", venue_label: null, received_at: "2026-07-28T07:00:01Z" },
  { open_time: "2026-07-28T07:00:00Z", close_time: "2026-07-28T08:00:00Z", open: "118000.00", high: "120000.00", low: "117500.00", close: "119000.00", source_label: "Synthetic historical candle source", venue_label: null, received_at: "2026-07-28T08:00:01Z" },
];

function HashNavigationProbe() {
  const navigate = useNavigate();
  return <button onClick={() => navigate("/#session-card")}>Open session hash</button>;
}

function renderDashboard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Dashboard />
        <HashNavigationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...view, client };
}

beforeEach(() => {
  auth.state = "valid";
  auth.telegramInitState = "TG_READY";
  auth.diagnosticCode = null;
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
  api.getCandles.mockReset().mockImplementation((_slug: string, requestedTimeframe: string) => (
    Promise.resolve({ timeframe: requestedTimeframe, items: candles })
  ));
});

describe("Stage 8 home dashboard", () => {
  it("shows the safe frontend build identifier on the authenticated dashboard", async () => {
    renderDashboard();

    await screen.findAllByText("119 000");
    expect(screen.getByLabelText("Сборка Mini App")).toHaveTextContent(
      /^[a-zA-Z0-9._-]+$/,
    );
  });

  it.each([
    ["browser", "TG_INIT_TIMEOUT", "Telegram не завершил инициализацию Mini App."],
    ["invalid", "AUTH_EXCHANGE_FAILED", "Не удалось подтвердить запуск через Telegram."],
    ["invalid", "SESSION_HEADER_MISSING", "Не удалось подтвердить запуск через Telegram."],
  ])("shows safe Russian auth diagnostics for %s / %s", (state, code, message) => {
    auth.state = state;
    auth.telegramInitState = code === "TG_INIT_TIMEOUT" ? "TG_INIT_TIMEOUT" : "TG_READY";
    auth.diagnosticCode = code;

    renderDashboard();

    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("alert")).toHaveTextContent(code);
    expect(screen.getByRole("alert")).toHaveTextContent(/Сборка: [a-zA-Z0-9._-]+/);
  });

  it("starts market queries immediately after authentication succeeds", async () => {
    auth.state = "browser";
    const { rerender, client } = renderDashboard();
    expect(api.getAssets).not.toHaveBeenCalled();

    auth.state = "valid";
    rerender(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <Dashboard />
          <HashNavigationProbe />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => expect(api.getQuotes).toHaveBeenCalledTimes(1));
    expect(api.getCandles).toHaveBeenCalledWith("btc-usdt", "1h");
  });

  it("uses bounded quote polling and refreshes after visibility and network restoration", async () => {
    const { client } = renderDashboard();
    await waitFor(() => expect(api.getQuotes).toHaveBeenCalledTimes(1));
    const quoteQuery = client.getQueryCache().getAll().find(
      (query) => query.queryKey[0] === "home-quotes",
    );
    const quoteOptions = quoteQuery?.options as { refetchInterval?: number } | undefined;
    expect(quoteOptions?.refetchInterval).toBe(60_000);

    try {
      focusManager.setFocused(false);
      focusManager.setFocused(true);
      await waitFor(() => expect(api.getQuotes).toHaveBeenCalledTimes(2));

      onlineManager.setOnline(false);
      onlineManager.setOnline(true);
      await waitFor(() => expect(api.getQuotes).toHaveBeenCalledTimes(3));
    } finally {
      focusManager.setFocused(true);
      onlineManager.setOnline(true);
    }
  });

  it("classifies synthetic provenance as DEMO and a non-synthetic source as LIVE", async () => {
    const liveQuote = {
      ...quoteFor("btc-usdt", "119000.00"),
      provenance: {
        ...quoteFor("btc-usdt", "119000.00").provenance,
        source_label: "Approved market feed",
      },
    };
    api.getQuotes.mockResolvedValue({ items: [liveQuote], unavailable: [], not_found: [] });
    const view = renderDashboard();
    expect((await screen.findAllByText("LIVE")).length).toBeGreaterThan(0);
    view.unmount();

    api.getQuotes.mockResolvedValue({
      items: [quoteFor("btc-usdt", "119000.00")],
      unavailable: [],
      not_found: [],
    });
    renderDashboard();
    expect((await screen.findAllByText("DEMO")).length).toBeGreaterThan(0);
  });

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
    expect(screen.getAllByLabelText("Bitcoin")[0]?.tagName).toBe("IMG");
    expect(screen.getAllByLabelText("Ethereum")[0]?.tagName).toBe("IMG");
    expect(screen.getAllByLabelText("Золото")[0]?.tagName).toBe("IMG");
    expect(screen.getByLabelText("Bitcoin на графике")).toBeInTheDocument();
    expect(document.querySelector('[data-icon="market-status-activity"]')).toBeInTheDocument();
    expect(screen.queryByText("$118,420.50")).not.toBeInTheDocument();
  });

  it("keeps the instrument chip and timeframe controls in one wrapping chart-controls region", async () => {
    renderDashboard();
    const select = await screen.findByRole("combobox", { name: "Инструмент графика" });
    const chip = select.closest("label");
    const controls = chip?.parentElement;

    expect(chip).toHaveClass("instrument-select");
    expect(controls).toHaveClass("chart-controls");
    expect(within(controls as HTMLElement).getByLabelText("Таймфрейм графика")).toBeInTheDocument();
    expect(chip).not.toHaveStyle({ position: "absolute" });
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

  it("does not render a late candle response under a newly selected instrument", async () => {
    let resolveBitcoin: ((value: { timeframe: string; items: typeof candles }) => void) | undefined;
    const bitcoinResponse = new Promise<{ timeframe: string; items: typeof candles }>((resolve) => {
      resolveBitcoin = resolve;
    });
    const ethereumCandles = candles.map((candle, index) => ({
      ...candle,
      open: index ? "4000.00" : "3900.00",
      high: index ? "4200.00" : "4100.00",
      low: index ? "3950.00" : "3850.00",
      close: index ? "4100.00" : "4000.00",
    }));
    api.getCandles.mockImplementation((slug: string) => (
      slug === "btc-usdt"
        ? bitcoinResponse
        : Promise.resolve({ timeframe: "1h", items: ethereumCandles })
    ));
    renderDashboard();
    await screen.findAllByText("119 000");

    fireEvent.click(screen.getByRole("button", { name: "Выбрать Ethereum" }));
    const chart = screen.getByRole("heading", { name: "Динамика цены" }).closest("section");
    expect(await within(chart as HTMLElement).findByText("4 050")).toBeInTheDocument();

    resolveBitcoin?.({ timeframe: "1h", items: candles });
    await waitFor(() => expect(within(chart as HTMLElement).getByText("4 050")).toBeInTheDocument());
    expect(screen.getByRole("combobox", { name: "Инструмент графика" })).toHaveValue("eth-usdt");
  });

  it("keeps a newer quote when an older refetch resolves last", async () => {
    const { client, container } = renderDashboard();
    await screen.findAllByText("119 000");

    let resolveOlder: ((value: ReturnType<typeof quotesResponse>) => void) | undefined;
    const older = new Promise<ReturnType<typeof quotesResponse>>((resolve) => {
      resolveOlder = resolve;
    });
    api.getQuotes
      .mockImplementationOnce(() => older)
      .mockResolvedValueOnce(quotesResponse("121000.00"));

    const queryKey = client.getQueryCache().getAll().find(
      (query) => query.queryKey[0] === "home-quotes",
    )?.queryKey;
    expect(queryKey).toBeDefined();
    void client.refetchQueries({ queryKey });
    await waitFor(() => expect(api.getQuotes).toHaveBeenCalledTimes(2));
    await client.refetchQueries({ queryKey });
    await waitFor(() => expect(container.querySelector(".hero-price")).toHaveTextContent("121 000"));

    resolveOlder?.(quotesResponse("120000.00"));
    await waitFor(() => expect(container.querySelector(".hero-price")).toHaveTextContent("121 000"));
  });

  it("calculates chart statistics from the normalized latest revisions", async () => {
    const oldDuplicate = {
      ...candles[0]!,
      high: "999999.00",
      close: "999999.00",
      received_at: "2026-07-28T07:00:00Z",
    };
    const latestRevision = {
      ...candles[0]!,
      high: "119200.00",
      close: "119100.00",
      received_at: "2026-07-28T07:00:02Z",
    };
    api.getCandles.mockResolvedValue({
      timeframe: "1h",
      items: [candles[1]!, oldDuplicate, latestRevision],
    });
    renderDashboard();
    const chart = (await screen.findByRole("heading", { name: "Динамика цены" })).closest("section");

    expect(await within(chart as HTMLElement).findByText("120 000")).toBeInTheDocument();
    expect(within(chart as HTMLElement).queryByText("999 999")).not.toBeInTheDocument();
  });

  it("scrolls the session card when the route hash changes after mount", async () => {
    const scrollIntoView = vi.fn();
    const originalDescriptor = Object.getOwnPropertyDescriptor(Element.prototype, "scrollIntoView");
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoView,
    });
    try {
      renderDashboard();
      await screen.findAllByText("119 000");
      scrollIntoView.mockClear();

      fireEvent.click(screen.getByRole("button", { name: "Open session hash" }));

      await waitFor(() => expect(scrollIntoView).toHaveBeenCalledWith({ block: "center" }));
    } finally {
      if (originalDescriptor) {
        Object.defineProperty(Element.prototype, "scrollIntoView", originalDescriptor);
      } else {
        delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView;
      }
    }
  });

  it("moves candle requests back to an available instrument after a catalog refresh", async () => {
    const { client } = renderDashboard();
    await screen.findAllByText("119 000");

    fireEvent.click(screen.getByRole("button", { name: "Выбрать Ethereum" }));
    await waitFor(() => expect(api.getCandles).toHaveBeenLastCalledWith("eth-usdt", "1h"));

    api.getAssets.mockResolvedValueOnce({ items: [assets[0], assets[2]], next_cursor: null });
    await client.refetchQueries({ queryKey: ["home-assets"] });

    await waitFor(() => expect(api.getCandles).toHaveBeenLastCalledWith("btc-usdt", "1h"));
    expect(screen.getAllByText("BTC/USDT").length).toBeGreaterThan(0);
  });

  it("uses one candle period when only half of the 24-hour range is available", async () => {
    api.getQuotes.mockResolvedValue({
      items: [{ ...quoteFor("btc-usdt", "119000.00"), high_24h: "125000.00", low_24h: null }],
      unavailable: [],
      not_found: [],
    });
    renderDashboard();

    expect(await screen.findByText("Макс. · 1h")).toBeInTheDocument();
    expect(screen.getByText("Мин. · 1h")).toBeInTheDocument();
    expect(screen.queryByText("125 000")).not.toBeInTheDocument();
    expect((await screen.findAllByText("120 000")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("115 500")).length).toBeGreaterThan(0);
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
    expect(screen.getByLabelText("Данные недоступны")).toBeInTheDocument();

    api.getQuotes.mockResolvedValue({
      items: [quoteFor("btc-usdt", "119000.00", "stale")],
      unavailable: [],
      not_found: [],
    });
    fireEvent.click(screen.getByRole("button", { name: "Повторить загрузку" }));
    await waitFor(() => expect(api.getQuotes).toHaveBeenCalledTimes(2));
    expect(
      await screen.findByText(/Данные устарели — показано последнее подтверждённое значение/),
    ).toBeInTheDocument();
  });

  it("distinguishes a quote request failure from a missing instrument", async () => {
    api.getQuotes.mockRejectedValueOnce(new Error("network unavailable"));
    renderDashboard();

    expect(await screen.findByText("Не удалось загрузить котировку")).toBeInTheDocument();
    expect(screen.queryByText("Котировка не найдена")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Данные недоступны")).toBeInTheDocument();
  });

  it("shows a safe diagnostic code and build marker for a protected catalog 401", async () => {
    api.getAssets.mockRejectedValueOnce(new ApiError("HTTP 401", 401));
    renderDashboard();

    expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось загрузить рынок");
    expect(screen.getByRole("alert")).toHaveTextContent("PROTECTED_API_401");
    expect(screen.getByRole("alert")).toHaveTextContent(/Сборка: [a-zA-Z0-9._-]+/);
    expect(screen.queryByText("HTTP 401")).not.toBeInTheDocument();
  });
});