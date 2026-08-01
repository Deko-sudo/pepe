import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAssets, getCandles, getMarketDataCapabilities, getQuote, type Candle, type Timeframe } from "@/shared/api/market";
import { useTelegramAuth } from "@/shared/telegram";
import { EmbeddedMarketChart } from "@/features/market-home/embedded-market-chart";

const timeframes: Timeframe[] = ["1m", "5m", "15m", "1h", "4h", "1d"];

// Exported for precision regression coverage; it does not hold component state.
// eslint-disable-next-line react-refresh/only-export-components
export function decimalToScaled(value: string, scale: number): bigint {
  const [whole = "0", fraction = ""] = value.replace(/^\+/, "").split(".");
  const sign = whole.startsWith("-") ? -1n : 1n;
  const digits = `${whole.replace("-", "")}${fraction.padEnd(scale, "0")}`.replace(/^0+/, "") || "0";
  return sign * BigInt(digits);
}

function decimalScale(value: string): number {
  return value.split(".")[1]?.length ?? 0;
}

function CandleChart({ candles }: { candles: Candle[] }) {
  const points = useMemo(() => {
    const scale = candles.reduce((maximum, candle) => Math.max(maximum, decimalScale(candle.close)), 0);
    const values = candles.map((candle) => decimalToScaled(candle.close, scale));
    const low = values.reduce((a, b) => a < b ? a : b, values[0] ?? 0n);
    const high = values.reduce((a, b) => a > b ? a : b, values[0] ?? 1n);
    const range = high - low || 1n;
    return values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${100 - Number(((value - low) * 10000n) / range) / 100}` ).join(" ");
  }, [candles]);
  if (!candles.length) return <p className="text-sm text-text-secondary">История свечей пока недоступна.</p>;
  return <svg viewBox="0 0 100 100" role="img" aria-label={`График из ${candles.length} закрытых свечей`} className="h-48 w-full overflow-visible"><polyline points={points} fill="none" stroke="var(--color-brand-primary)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" /></svg>;
}

export function Markets() {
  const { state: authState } = useTelegramAuth();
  const [selectedSlug, setSelectedSlug] = useState<string>();
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const catalog = useQuery({ queryKey: ["assets"], queryFn: getAssets, enabled: authState === "valid" });
  const capabilities = useQuery({ queryKey: ["market-data-capabilities"], queryFn: getMarketDataCapabilities, enabled: authState === "valid", retry: false });
  useEffect(() => { if (!selectedSlug && catalog.data?.items[0]) setSelectedSlug(catalog.data.items[0].slug); }, [catalog.data, selectedSlug]);
  const hasSession = authState === "valid";
  const machineReadableMarketData = capabilities.data?.numeric_quotes_available === true && capabilities.data.server_candles_available === true;
  const embeddedMode = capabilities.data?.mode === "embedded";
  const embeddedWrapperAvailable = embeddedMode
    && capabilities.data?.embedded_chart_available === true
    && capabilities.data.embedded_chart_provider === "tradingview_isolated_wrapper"
    && capabilities.data.embedded_chart_config_version === 1;
  const canLoadMarket = hasSession && Boolean(selectedSlug) && machineReadableMarketData;
  const quote = useQuery({ queryKey: ["quote", selectedSlug], queryFn: () => getQuote(selectedSlug!), enabled: canLoadMarket, refetchInterval: canLoadMarket ? 30_000 : false });
  const candles = useQuery({ queryKey: ["candles", selectedSlug, timeframe], queryFn: () => getCandles(selectedSlug!, timeframe), enabled: canLoadMarket, refetchInterval: canLoadMarket ? 60_000 : false });
  const currentQuote = hasSession ? quote.data?.items.find((item) => item.slug === selectedSlug) : undefined;
  const quoteState = hasSession && quote.data?.unavailable.includes(selectedSlug ?? "") ? "Котировка временно недоступна" : hasSession && quote.data?.not_found.includes(selectedSlug ?? "") ? "Инструмент не найден" : null;
  const retry = () => { void catalog.refetch(); void capabilities.refetch(); if (canLoadMarket) { void quote.refetch(); void candles.refetch(); } };

  return <div className="flex h-full flex-col gap-4 overflow-y-auto p-4 pb-24">
    <header className="safe-area-top"><h1 className="text-2xl font-bold text-text-primary">Рынки</h1><p className="mt-1 text-sm text-text-secondary">Данные обновляются из защищённого API</p></header>
    {authState === "validating" || catalog.isLoading ? <div className="card" role="status">Загрузка каталога…</div> : null}
    {authState === "browser" || authState === "invalid" || authState === "unavailable" ? <div className="card" role="alert">Для просмотра рынков требуется подтверждённая сессия Telegram.</div> : null}
    {catalog.isError ? <div className="card" role="alert">Не удалось загрузить каталог. <button className="underline" onClick={retry}>Повторить</button></div> : null}
    {catalog.data?.items.length === 0 ? <div className="card">Доступные инструменты отсутствуют.</div> : null}
    {catalog.data?.items.length ? <label className="card flex flex-col gap-2 text-sm font-medium">Инструмент<select aria-label="Выбор инструмента" value={selectedSlug} onChange={(event) => setSelectedSlug(event.target.value)} className="touch-target rounded-lg border border-border-subtle bg-transparent px-3">{catalog.data.items.map((asset) => <option key={asset.id} value={asset.slug}>{asset.display_name} ({asset.symbol})</option>)}</select></label> : null}
    {hasSession && capabilities.isError ? <section className="card" role="alert"><h2 className="text-sm font-medium text-text-secondary">Не удалось определить доступность рыночных данных</h2><button className="mt-2 underline" onClick={retry}>Повторить</button></section> : null}
    {hasSession && embeddedMode ? <><section className="card"><div className="flex flex-wrap gap-2" role="group" aria-label="Таймфрейм графика">{timeframes.map((value) => <button key={value} aria-pressed={timeframe === value} onClick={() => setTimeframe(value)} className={`touch-target rounded-lg border px-3 text-sm ${timeframe === value ? "border-brand-primary text-brand-primary" : "border-border-subtle"}`}>{value}</button>)}</div></section>{selectedSlug ? <EmbeddedMarketChart slug={selectedSlug} timeframe={timeframe} enabled={embeddedWrapperAvailable} /> : null}</> : null}
    {hasSession && !capabilities.isLoading && !capabilities.isError && !machineReadableMarketData && !embeddedMode ? <section className="card" role="status" aria-live="polite"><h2 className="text-sm font-medium text-text-secondary">Рыночные данные недоступны</h2><p className="mt-2 text-sm">Внешний источник графика ещё не настроен. Числовые котировки и свечи сейчас не отображаются.</p></section> : null}
    {canLoadMarket ? <><section className="card" aria-live="polite"><h2 className="text-sm font-medium text-text-secondary">Текущая котировка</h2>{quote.isLoading ? <p className="mt-2">Загрузка…</p> : currentQuote ? <><p className="mt-2 text-3xl font-bold tabular-nums">{currentQuote.price}</p><p className="mt-2 text-xs text-text-secondary">Источник: {currentQuote.provenance.source_label}; наблюдение {new Date(currentQuote.observed_at).toLocaleString()}</p>{currentQuote.data_status === "stale" ? <p className="mt-2 text-sm" role="status">Котировка устарела; ожидается обновление источника.</p> : null}</> : <p className="mt-2 text-sm">{quoteState ?? "Котировка недоступна"}</p>}{quote.isError ? <button className="mt-2 underline" onClick={retry}>Повторить</button> : null}</section>
    <section className="card"><div className="flex flex-wrap gap-2" role="group" aria-label="Таймфрейм">{timeframes.map((value) => <button key={value} aria-pressed={timeframe === value} onClick={() => setTimeframe(value)} className={`touch-target rounded-lg border px-3 text-sm ${timeframe === value ? "border-brand-primary text-brand-primary" : "border-border-subtle"}`}>{value}</button>)}</div><h2 className="mt-4 text-sm font-medium text-text-secondary">Закрытые свечи · {timeframe}</h2>{candles.isLoading ? <p className="mt-4" role="status">Загрузка истории…</p> : candles.isError ? <p className="mt-4" role="alert">Не удалось загрузить свечи. <button className="underline" onClick={retry}>Повторить</button></p> : <CandleChart candles={candles.data?.items ?? []} />}</section></> : null}
  </div>;
}
