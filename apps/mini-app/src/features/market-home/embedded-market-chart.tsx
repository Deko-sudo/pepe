import { useEffect, useState } from "react";
import type { EmbeddedChartConfig } from "@/shared/api/market";

export function EmbeddedMarketChart({ config, onRetry }: { config: EmbeddedChartConfig; onRetry: () => void }) {
  const [loaded, setLoaded] = useState(false);
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    setLoaded(false);
    setTimedOut(false);
    const timeout = window.setTimeout(() => setTimedOut(true), 12_000);
    return () => window.clearTimeout(timeout);
  }, [config.iframe_url]);

  return <section className="card" aria-live="polite">
    <h2 className="text-sm font-medium text-text-secondary">{config.display_name} · {config.interval}</h2>
    {!loaded && !timedOut ? <p className="mt-3 text-sm" role="status">Загрузка графика TradingView…</p> : null}
    {timedOut ? <p className="mt-3 text-sm" role="alert">График не загрузился. <button className="underline" onClick={onRetry}>Повторить</button></p> : null}
    <iframe
      className="mt-3 h-80 w-full rounded-lg border border-border-subtle bg-background"
      src={config.iframe_url}
      title={`TradingView chart: ${config.display_name}, ${config.interval}`}
      referrerPolicy="strict-origin"
      onLoad={() => { setLoaded(true); setTimedOut(false); }}
    />
    <p className="mt-3 text-xs text-text-secondary">Источник: {config.source_label}. {config.market_semantics}. {config.delay_disclosure}</p>
    <p className="mt-2 text-xs text-text-secondary">{config.attribution}</p>
    <a className="mt-3 inline-block underline" href={config.fallback_url} target="_blank" rel="noopener noreferrer">Открыть в TradingView</a>
  </section>;
}
