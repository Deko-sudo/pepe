import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EmbeddedMarketChart } from "../src/features/market-home/embedded-market-chart";

const configuration = {
  version: 1,
  mode: "embedded",
  provider: "tradingview_isolated_wrapper",
  asset: "btc-usdt",
  timeframe: "1h",
  wrapper_origin: "http://127.0.0.1:4173",
  wrapper_path: "/chart/btc-usdt/1h",
  wrapper_url: "http://127.0.0.1:4173/chart/btc-usdt/1h",
};

function renderChart(props: Partial<React.ComponentProps<typeof EmbeddedMarketChart>> = {}) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><EmbeddedMarketChart slug="btc-usdt" timeframe="1h" enabled {...props} /></QueryClientProvider>);
}

afterEach(() => vi.restoreAllMocks());

describe("EmbeddedMarketChart", () => {
  it("renders only the validated server URL with the exact W2 iframe contract", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(configuration), { status: 200 }));
    const { container } = renderChart();
    const frame = await waitFor(() => {
      const element = container.querySelector("iframe");
      if (!element) throw new Error("iframe not mounted");
      return element;
    });
    expect(frame).toHaveAttribute("src", configuration.wrapper_url);
    expect(frame).toHaveAttribute("sandbox", "allow-scripts allow-same-origin");
    expect(frame).toHaveAttribute("referrerpolicy", "no-referrer");
    expect(frame).toHaveAttribute("title", "Встроенный график btc-usdt · 1h");
    expect(frame).not.toHaveAttribute("allow");
    expect(frame).not.toHaveAttribute("srcdoc");
  });

  it("does not request configuration or create an iframe when unavailable", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = renderChart({ enabled: false });
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("keeps lifecycle document loading semantically readiness-unknown", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(configuration), { status: 200 }));
    const { container } = renderChart();
    const frame = await waitFor(() => {
      const element = container.querySelector("iframe");
      if (!element) throw new Error("iframe not mounted");
      return element as HTMLIFrameElement;
    });
    fireEvent(window, new MessageEvent("message", {
      origin: configuration.wrapper_origin,
      source: frame.contentWindow,
      data: { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-document-loaded" },
    }));
    await waitFor(() => expect(screen.getByText(/готовность источника неизвестна/i)).toBeInTheDocument());
    expect(container.textContent).not.toMatch(/provider ready|real-time|streaming|connected/i);
  });

  it.each([
    ["wrong origin", "http://127.0.0.1:4174", { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout" }],
    ["parent origin", window.location.origin, { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout" }],
    ["TradingView origin", "https://www.tradingview.com", { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout" }],
    ["suffix-confusion origin", "http://127.0.0.1:4173.attacker.test", { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout" }],
    ["port mismatch", "http://127.0.0.1:4174", { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout" }],
    ["scheme mismatch", "https://127.0.0.1:4173", { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout" }],
    ["null origin", "null", { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout" }],
    ["empty origin", "", { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout" }],
    ["string payload", configuration.wrapper_origin, "provider-frame-timeout"],
    ["array payload", configuration.wrapper_origin, ["provider-frame-timeout"]],
    ["null payload", configuration.wrapper_origin, null],
    ["unknown event", configuration.wrapper_origin, { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-ready" }],
    ["unknown type", configuration.wrapper_origin, { type: "provider.lifecycle", version: 1, event: "provider-frame-timeout" }],
    ["unknown version", configuration.wrapper_origin, { type: "pepe.tradingview-wrapper.lifecycle", version: 2, event: "provider-frame-timeout" }],
    ["extra payload field", configuration.wrapper_origin, { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout", price: "1" }],
  ])("rejects lifecycle payload with %s", async (_, origin, data) => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(configuration), { status: 200 }));
    const { container } = renderChart();
    const frame = await waitFor(() => {
      const element = container.querySelector("iframe");
      if (!element) throw new Error("iframe not mounted");
      return element as HTMLIFrameElement;
    });
    fireEvent(window, new MessageEvent("message", { origin, source: frame.contentWindow, data }));
    expect(screen.queryByText(/временно недоступен/i)).not.toBeInTheDocument();
  });

  it("rejects an otherwise-valid message from a non-frame source", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(configuration), { status: 200 }));
    const { container } = renderChart();
    await waitFor(() => {
      if (!container.querySelector("iframe")) throw new Error("iframe not mounted");
    });

    fireEvent(window, new MessageEvent("message", {
      origin: configuration.wrapper_origin,
      source: window,
      data: { type: "pepe.tradingview-wrapper.lifecycle", version: 1, event: "provider-frame-timeout" },
    }));

    expect(screen.queryByText(/временно недоступен/i)).not.toBeInTheDocument();
  });

  it("keeps the newer selection when a cancelled prior configuration settles late", async () => {
    let resolveFirst: (response: Response) => void;
    const first = new Promise<Response>((resolve) => { resolveFirst = resolve; });
    const secondConfiguration = {
      ...configuration,
      asset: "eth-usdt",
      wrapper_path: "/chart/eth-usdt/1h",
      wrapper_url: "http://127.0.0.1:4173/chart/eth-usdt/1h",
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockReturnValueOnce(first)
      .mockResolvedValueOnce(new Response(JSON.stringify(secondConfiguration), { status: 200 }));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const subject = (slug: string) => <QueryClientProvider client={client}><EmbeddedMarketChart slug={slug} timeframe="1h" enabled /></QueryClientProvider>;
    const view = render(subject("btc-usdt"));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));

    view.rerender(subject("eth-usdt"));
    const currentFrame = await waitFor(() => {
      const frame = view.container.querySelector("iframe");
      if (!frame || frame.getAttribute("src") !== secondConfiguration.wrapper_url) throw new Error("new iframe not mounted");
      return frame;
    });
    resolveFirst!(new Response(JSON.stringify(configuration), { status: 200 }));

    await waitFor(() => expect(view.container.querySelector("iframe")).toBe(currentFrame));
    expect(currentFrame).toHaveAttribute("src", secondConfiguration.wrapper_url);
  });
});
