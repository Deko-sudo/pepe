import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getEmbeddedChartConfiguration,
  type EmbeddedChartConfiguration,
  type Timeframe,
  validateEmbeddedChartConfiguration,
} from "@/shared/api/market";
import { ApiError } from "@/shared/api/client";

const LIFECYCLE_EVENTS = [
  "wrapper-document-ready",
  "provider-script-load-failed",
  "provider-frame-created",
  "provider-frame-document-loaded",
  "provider-frame-timeout",
  "wrapper-configuration-invalid",
] as const;

type LifecycleEvent = (typeof LIFECYCLE_EVENTS)[number];
type ChartState = "loading" | "navigating" | "wrapper-loaded" | "readiness-unknown" | "unavailable" | "invalid" | "unsupported";

function isLifecycleMessage(value: unknown): value is { type: "pepe.tradingview-wrapper.lifecycle"; version: 1; event: LifecycleEvent } {
  if (!value || typeof value !== "object" || Array.isArray(value) || Object.keys(value).length !== 3) return false;
  const payload = value as Record<string, unknown>;
  return payload.type === "pepe.tradingview-wrapper.lifecycle" && payload.version === 1 &&
    typeof payload.event === "string" && (LIFECYCLE_EVENTS as readonly string[]).includes(payload.event);
}

const messages: Record<ChartState, string> = {
  loading: "Проверяем конфигурацию графика…",
  navigating: "График загружается…",
  "wrapper-loaded": "Документ графика загружен; доступность источника ещё не подтверждена.",
  "readiness-unknown": "График отображается; готовность источника неизвестна.",
  unavailable: "Источник встроенного графика временно недоступен.",
  invalid: "Конфигурация встроенного графика отклонена.",
  unsupported: "Встроенный график не поддерживается этой конфигурацией.",
};

type EmbeddedMarketChartProps = {
  slug: string;
  timeframe: Timeframe;
  enabled: boolean;
} | { state: "provider-not-configured" };

export function EmbeddedMarketChart(props: EmbeddedMarketChartProps) {
  if ("state" in props) return <ChartStatus state="unsupported" />;
  return <IsolatedEmbeddedMarketChart {...props} />;
}

function IsolatedEmbeddedMarketChart({ slug, timeframe, enabled }: Exclude<EmbeddedMarketChartProps, { state: "provider-not-configured" }>) {
  const queryClient = useQueryClient();
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [state, setState] = useState<ChartState>(enabled ? "loading" : "unsupported");
  const configuration = useQuery({
    queryKey: ["embedded-chart-configuration", slug, timeframe],
    queryFn: async ({ signal }) => validateEmbeddedChartConfiguration(
      await getEmbeddedChartConfiguration(slug, timeframe, signal), slug, timeframe, window.location.origin,
    ),
    enabled,
    retry: false,
  });

  useEffect(() => {
    if (!enabled) void queryClient.cancelQueries({ queryKey: ["embedded-chart-configuration", slug, timeframe] });
  }, [enabled, queryClient, slug, timeframe]);
  useEffect(() => { setState(enabled ? "loading" : "unsupported"); }, [enabled, slug, timeframe]);
  const validConfiguration: EmbeddedChartConfiguration | null = configuration.data ?? null;

  useEffect(() => {
    if (!validConfiguration) return;
    setState("navigating");
    const origin = new URL(validConfiguration.wrapper_origin).origin;
    const timeout = window.setTimeout(() => setState("unavailable"), 10_000);
    const onMessage = (event: MessageEvent<unknown>) => {
      const frame = frameRef.current;
      if (!frame || event.origin === "null" || event.origin !== origin || event.source !== frame.contentWindow || !isLifecycleMessage(event.data)) return;
      window.clearTimeout(timeout);
      if (event.data.event === "provider-script-load-failed" || event.data.event === "provider-frame-timeout") setState("unavailable");
      else if (event.data.event === "wrapper-configuration-invalid") setState("invalid");
      else if (event.data.event === "provider-frame-document-loaded") setState("readiness-unknown");
      else if (event.data.event === "wrapper-document-ready") setState("wrapper-loaded");
    };
    window.addEventListener("message", onMessage);
    return () => {
      window.clearTimeout(timeout);
      window.removeEventListener("message", onMessage);
    };
  }, [validConfiguration]);

  if (!enabled) return <ChartStatus state="unsupported" />;
  if (configuration.isLoading) return <ChartStatus state="loading" />;
  if (configuration.isError) {
    if (configuration.error instanceof ApiError && configuration.error.status === 409) return <ChartStatus state="unavailable" />;
    return <section className="card" aria-live="polite"><h2 className="text-sm font-medium text-text-secondary">Встроенный график</h2><p className="mt-3 text-sm" role="alert">{messages.invalid}</p><button className="mt-2 underline" onClick={() => { void configuration.refetch(); }}>Повторить</button></section>;
  }
  if (!validConfiguration) return <ChartStatus state="invalid" />;

  return <section className="card" aria-live="polite">
    <h2 className="text-sm font-medium text-text-secondary">Встроенный график</h2>
    <p className="mt-3 text-sm" role={state === "unavailable" || state === "invalid" ? "alert" : "status"}>{messages[state]}</p>
    <iframe
      ref={frameRef}
      className="mt-3 h-80 w-full border-0"
      src={validConfiguration.wrapper_url}
      sandbox="allow-scripts allow-same-origin"
      referrerPolicy="no-referrer"
      title={`Встроенный график ${slug} · ${timeframe}`}
      onLoad={() => setState((current) => current === "navigating" ? "wrapper-loaded" : current)}
    />
  </section>;
}

function ChartStatus({ state }: { state: ChartState }) {
  return <section className="card" aria-live="polite"><h2 className="text-sm font-medium text-text-secondary">Встроенный график</h2><p className="mt-3 text-sm" role={state === "unavailable" || state === "invalid" ? "alert" : "status"}>{messages[state]}</p></section>;
}
