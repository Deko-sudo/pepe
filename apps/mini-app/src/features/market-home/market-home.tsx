import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  ChevronRight,
  Clock3,
  Info,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import {
  getAssets,
  getCandles,
  getMarketDataCapabilities,
  getQuotes,
  TIMEFRAMES,
  type Asset,
  type Quote,
  type Timeframe,
} from "@/shared/api/market";
import {
  BUILD_ID,
  marketDiagnosticCode,
  type DiagnosticCode,
} from "@/shared/diagnostics";
import { candleStatistics, formatDecimal, formatSignedDecimal } from "@/shared/lib/decimal";
import { useModalStore } from "@/shared/lib/store";
import { useTelegramAuth } from "@/shared/telegram";
import { Modal } from "@/shared/ui/modal";
import { EmbeddedMarketChart } from "./embedded-market-chart";

import { AssetIcon } from "./asset-icon";
import { normalizeCandles } from "./chart-data";
import { quoteFreshness } from "./freshness";
import { MarketChart } from "./market-chart";

const TRACKED_SLUGS = ["btc-usdt", "eth-usdt", "xau-usd"];

function provenanceMode(sourceLabel?: string | null) {
  return sourceLabel && /^(synthetic|fake|fixture|demo|test)(?:\b|[-_ ])/i.test(sourceLabel)
    ? "DEMO"
    : "LIVE";
}

function marketStatusText(status: string) {
  if (status === "open") return "Рынок открыт";
  if (status === "closed") return "Рынок закрыт";
  return "Статус рынка уточняется";
}

function displayMarketType(asset: Asset) {
  if (asset.market_type === "spot") return "Спот-рынок";
  return asset.market_type;
}

function DashboardSkeleton() {
  return (
    <main className="market-home" aria-label="Загрузка обзора рынка" aria-busy="true">
      <div className="home-skeleton skeleton-heading" />
      <div className="home-skeleton skeleton-hero" />
      <div className="grid grid-cols-3 gap-2">
        {[0, 1, 2].map((item) => <div key={item} className="home-skeleton skeleton-action" />)}
      </div>
      <div className="home-skeleton skeleton-card" />
      <div className="home-skeleton skeleton-feed" />
      <div className="home-skeleton skeleton-chart" />
    </main>
  );
}

function BlockingState({
  title,
  message,
  diagnosticCode,
  retry,
}: {
  title: string;
  message: string;
  diagnosticCode?: DiagnosticCode;
  retry?: () => void;
}) {
  return (
    <main className="market-home">
      <section className="home-state" role="alert">
        <span className="state-icon" aria-hidden="true"><AlertTriangle size={20} /></span>
        <h1>{title}</h1>
        <p>{message}</p>
        {diagnosticCode ? (
          <p className="state-diagnostic">Код: {diagnosticCode} · Сборка: {BUILD_ID}</p>
        ) : null}
        {retry ? (
          <button className="retry-button" onClick={retry} type="button">
            <RefreshCw size={15} aria-hidden="true" />
            Повторить загрузку
          </button>
        ) : null}
      </section>
    </main>
  );
}

function QuickActions() {
  const actions = [
    { label: "Рынки", accessible: "Открыть рынки", href: "/markets", icon: BarChart3 },
    { label: "Сессия", accessible: "Перейти к сессии", href: "#session-card", icon: ShieldCheck },
    { label: "О Pepe", accessible: "Как это работает", href: "#ai-support", icon: Info },
  ];
  return (
    <nav className="quick-actions" aria-label="Быстрые действия">
      {actions.map(({ label, accessible, href, icon: Icon }) => href.startsWith("/") ? (
        <Link key={href} className="quick-action" to={href} aria-label={accessible}>
          <span><Icon size={19} strokeWidth={1.7} aria-hidden="true" /></span>
          <b>{label}</b>
        </Link>
      ) : (
        <a key={href} className="quick-action" href={href} aria-label={accessible}>
          <span><Icon size={19} strokeWidth={1.7} aria-hidden="true" /></span>
          <b>{label}</b>
        </a>
      ))}
    </nav>
  );
}

interface HeroCardProps {
  asset: Asset;
  quote?: Quote;
  freshnessElapsedSeconds: number;
  stats: ReturnType<typeof candleStatistics>;
  timeframe: Timeframe;
  loading: boolean;
  unavailable: boolean;
  error: boolean;
  onRetry: () => void;
}

function HeroCard({ asset, quote, freshnessElapsedSeconds, stats, timeframe, loading, unavailable, error, onRetry }: HeroCardProps) {
  const hasQuoteRange = quote?.high_24h != null && quote.low_24h != null;
  const high = hasQuoteRange ? quote.high_24h : stats?.high;
  const low = hasQuoteRange ? quote.low_24h : stats?.low;
  const rangeLabel = hasQuoteRange ? "24 ч" : timeframe;
  const freshness = quote ? quoteFreshness(quote, freshnessElapsedSeconds) : null;
  return (
    <section className="market-hero enter-card">
      <div className="hero-geometry" aria-hidden="true"><i /><i /><i /></div>
      <header className="hero-head">
        <div className="asset-identity">
          <AssetIcon asset={asset.base_asset ?? asset.symbol.split("/")[0] ?? asset.symbol} label={asset.display_name} size="lg" />
          <div>
            <span>{asset.symbol}</span>
            <strong>{asset.display_name}</strong>
          </div>
        </div>
        <span className={`provenance-badge ${quote && provenanceMode(quote.provenance.source_label) === "LIVE" ? "is-live" : "is-demo"}`}>
          <i aria-hidden="true" />{quote ? provenanceMode(quote.provenance.source_label) : "—"}
        </span>
      </header>

      <div className="hero-price-wrap" aria-live="polite">
        <span className="eyebrow">Текущая цена</span>
        {loading ? <span className="home-skeleton skeleton-price" /> : quote ? (
          <strong className="hero-price number-change">{formatDecimal(quote.price, asset.price_precision)}</strong>
        ) : (
          <div className="quote-unavailable">
            <strong>{error ? "Не удалось загрузить котировку" : unavailable ? "Котировка временно недоступна" : "Котировка не найдена"}</strong>
            <button type="button" onClick={onRetry} aria-label="Повторить загрузку"><RefreshCw size={14} /></button>
          </div>
        )}
        {quote ? (
          <span className="hero-freshness">
            <i className={freshness?.stale ? "is-stale" : ""} aria-hidden="true" />
            {freshness?.text}
          </span>
        ) : null}
        {quote?.change_percent_24h ? (
          <span className={`hero-change ${quote.change_percent_24h.startsWith("-") ? "is-negative" : "is-positive"}`}>
            {formatSignedDecimal(quote.change_percent_24h, 2)}%
            <small>24 ч</small>
          </span>
        ) : null}
      </div>

      <dl className="hero-stats">
        <div><dt>Макс. · {rangeLabel}</dt><dd>{high ? formatDecimal(high, asset.price_precision) : "—"}</dd></div>
        <div><dt>Мин. · {rangeLabel}</dt><dd>{low ? formatDecimal(low, asset.price_precision) : "—"}</dd></div>
        <div><dt>Источник</dt><dd>{quote?.provenance.source_label ?? "Нет данных"}</dd></div>
      </dl>
    </section>
  );
}

function DataContext({ quote, freshnessElapsedSeconds }: { quote?: Quote; freshnessElapsedSeconds: number }) {
  const freshness = quote ? quoteFreshness(quote, freshnessElapsedSeconds) : null;
  const statusClass = freshness?.stale ? "is-stale" : quote ? "is-fresh" : "is-unavailable";
  const statusLabel = freshness?.stale ? "Данные устарели" : quote ? "Данные актуальны" : "Данные недоступны";
  return (
    <section className="context-card enter-card" aria-labelledby="market-context-title">
      <span className="context-icon" data-icon="market-status-activity" aria-hidden="true">
        <Activity size={22} strokeWidth={1.7} />
      </span>
      <div className="context-copy">
        <span className="eyebrow" id="market-context-title">Состояние данных</span>
        <strong>{quote ? marketStatusText(quote.market_status) : "Ожидание котировки"}</strong>
        <p>{quote ? `Последнее наблюдение: ${freshness?.text}.` : "Провайдер пока не вернул котировку."}</p>
        {quote ? <small className="context-meta">{quote.provenance.price_type} · {quote.provenance.delay_class}</small> : null}
        <div className={`freshness-track ${statusClass}`} aria-label={statusLabel}><i /></div>
      </div>
    </section>
  );
}

interface MarketFeedProps {
  assets: Asset[];
  quotes: Quote[];
  freshnessElapsedSeconds: number;
  unavailable: string[];
  notFound: string[];
  selectedSlug: string;
  onSelect: (slug: string) => void;
}

function MarketFeed({ assets, quotes, freshnessElapsedSeconds, unavailable, notFound, selectedSlug, onSelect }: MarketFeedProps) {
  const quoteMap = new Map(quotes.map((quote) => [quote.slug, quote]));
  const feedMode = quotes.length > 0 && quotes.every((quote) => provenanceMode(quote.provenance.source_label) === "LIVE") ? "LIVE" : "DEMO";
  return (
    <section className="market-feed enter-card" aria-labelledby="feed-title">
      <header className="section-heading">
        <div><span className="section-kicker">Рынок сейчас</span><h2 id="feed-title">Лента</h2></div>
        <span className={`feed-mode ${feedMode === "LIVE" ? "is-live" : "is-demo"}`}><i />{feedMode}</span>
      </header>
      <div className="feed-list">
        {assets.map((asset) => {
          const quote = quoteMap.get(asset.slug);
          const freshness = quote ? quoteFreshness(quote, freshnessElapsedSeconds) : null;
          const isUnavailable = unavailable.includes(asset.slug);
          const isNotFound = notFound.includes(asset.slug);
          return (
            <button
              key={asset.slug}
              type="button"
              className={`feed-row ${selectedSlug === asset.slug ? "is-selected" : ""}`}
              onClick={() => onSelect(asset.slug)}
              aria-label={`Выбрать ${asset.display_name}`}
              aria-pressed={selectedSlug === asset.slug}
            >
              <AssetIcon asset={asset.base_asset ?? asset.symbol.split("/")[0] ?? asset.symbol} label={asset.display_name} />
              <span className="feed-name"><strong>{asset.symbol}</strong><small>{quote?.provenance.source_label ?? displayMarketType(asset)}</small></span>
              <span className="feed-value">
                <strong>{quote ? formatDecimal(quote.price, asset.price_precision) : isUnavailable ? "Недоступно" : isNotFound ? "Не найдено" : "—"}</strong>
                <small className={freshness?.stale ? "stale-text" : ""}>{freshness?.text ?? displayMarketType(asset)}</small>
              </span>
              <ChevronRight size={15} aria-hidden="true" />
            </button>
          );
        })}
      </div>
    </section>
  );
}

interface ChartCardProps {
  assets: Asset[];
  selected: Asset;
  selectedSlug: string;
  onSelect: (slug: string) => void;
  timeframe: Timeframe;
  onTimeframe: (timeframe: Timeframe) => void;
  candles: Awaited<ReturnType<typeof getCandles>> | undefined;
  loading: boolean;
  error: boolean;
  retry: () => void;
}

function ChartCard({ assets, selected, selectedSlug, onSelect, timeframe, onTimeframe, candles, loading, error, retry }: ChartCardProps) {
  const items = normalizeCandles(candles?.items ?? []);
  const stats = candleStatistics(items);
  const mode = provenanceMode(items[0]?.source_label);
  return (
    <section className="chart-card enter-card" aria-labelledby="chart-title">
      <header className="section-heading chart-heading">
        <div><span className="section-kicker">PostgreSQL · свечи</span><h2 id="chart-title">Динамика цены</h2></div>
        <span className={`provenance-badge ${mode === "LIVE" ? "is-live" : "is-demo"}`}><i />{items.length ? mode : "—"}</span>
      </header>
      <div className="chart-controls">
        <label className="instrument-select">
          <AssetIcon asset={selected.base_asset ?? selected.symbol.split("/")[0] ?? selected.symbol} label={`${selected.display_name} на графике`} size="sm" />
          <span className="sr-only">Инструмент графика</span>
          <select value={selectedSlug} onChange={(event) => onSelect(event.target.value)} aria-label="Инструмент графика">
            {assets.map((asset) => <option key={asset.slug} value={asset.slug}>{asset.symbol}</option>)}
          </select>
        </label>
        <div className="timeframe-tabs" aria-label="Таймфрейм графика">
          {TIMEFRAMES.map((item) => (
            <button key={item} type="button" className={item === timeframe ? "is-active" : ""} onClick={() => onTimeframe(item)} aria-pressed={item === timeframe}>{item}</button>
          ))}
        </div>
      </div>
      <div className="chart-stage">
        {loading ? <div className="home-skeleton skeleton-chart-inner" /> : error ? (
          <div className="chart-error" role="alert"><span>Не удалось загрузить свечи</span><button onClick={retry} type="button">Повторить</button></div>
        ) : <MarketChart candles={items} />}
      </div>
      <dl className="chart-stats">
        <div><dt>Максимум</dt><dd>{stats ? formatDecimal(stats.high, selected.price_precision) : "—"}</dd></div>
        <div><dt>Минимум</dt><dd>{stats ? formatDecimal(stats.low, selected.price_precision) : "—"}</dd></div>
        <div><dt>Среднее</dt><dd>{stats ? formatDecimal(stats.average, selected.price_precision) : "—"}</dd></div>
        <div><dt>Диапазон</dt><dd>{stats ? formatDecimal(stats.range, selected.price_precision) : "—"}</dd></div>
      </dl>
    </section>
  );
}

function InformationCards({ asset }: { asset: Asset }) {
  const { aiSupportOpen, openAiSupport, closeAiSupport } = useModalStore();
  const aiSupportButtonRef = useRef<HTMLButtonElement>(null);
  const continuous = asset.calendar_kind === "always_open" || asset.trading_calendar === "crypto-24x7";
  return (
    <div className="info-grid">
      <section id="session-card" className="info-card enter-card" aria-labelledby="session-title">
        <span className="info-icon" aria-hidden="true"><Clock3 size={21} strokeWidth={1.6} /></span>
        <div><span className="section-kicker">{asset.timezone}</span><h2 id="session-title">Торговая сессия</h2><strong>{continuous ? "Круглосуточный рынок" : asset.trading_calendar}</strong><p>Информационный календарь инструмента без оценки влияния на рынок.</p></div>
      </section>
      <button ref={aiSupportButtonRef} id="ai-support" className="info-card ai-card enter-card" onClick={openAiSupport} type="button" aria-haspopup="dialog" aria-label="Открыть AI-поддержку">
        <span className="ai-mark" aria-hidden="true">AI<Sparkles size={12} /></span>
        <div><span className="section-kicker">Beta</span><h2>AI-поддержка</h2><strong>Справочный раздел</strong><p>Навигация по возможностям Pepe. Рыночные выводы не формируются.</p></div>
        <ChevronRight className="info-chevron" size={17} aria-hidden="true" />
      </button>
      <Modal isOpen={aiSupportOpen} onClose={closeAiSupport} title="AI-поддержка · Beta" returnFocusRef={aiSupportButtonRef}>
        <p className="text-sm leading-relaxed text-text-secondary">Раздел находится в разработке. Сейчас Pepe показывает только фактические рыночные данные и не формирует торговые рекомендации.</p>
      </Modal>
    </div>
  );
}

export function MarketHome() {
  const location = useLocation();
  const { state, telegramInitState, diagnosticCode } = useTelegramAuth();
  const canLoadMarket = state === "valid";
  const capabilities = useQuery({ queryKey: ["market-data-capabilities"], queryFn: getMarketDataCapabilities, enabled: canLoadMarket, retry: false });
  const hasMachineReadableMarketData = capabilities.data?.numeric_quotes_available === true && capabilities.data.server_candles_available === true;
  const [selectedSlug, setSelectedSlug] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const [freshnessClock, setFreshnessClock] = useState(() => Date.now());
  const catalog = useQuery({
    queryKey: ["home-assets"],
    queryFn: getAssets,
    enabled: canLoadMarket,
    refetchOnWindowFocus: "always",
    refetchOnReconnect: "always",
  });
  const trackedAssets = useMemo(() => {
    const items = catalog.data?.items ?? [];
    const preferred = TRACKED_SLUGS.map((slug) => items.find((item) => item.slug === slug)).filter((item): item is Asset => Boolean(item));
    return preferred.length ? preferred : items.slice(0, 3);
  }, [catalog.data]);
  const selectedAsset = trackedAssets.find((asset) => asset.slug === selectedSlug) ?? trackedAssets[0];
  const activeSlug = selectedAsset?.slug ?? "";

  useEffect(() => {
    if (activeSlug && activeSlug !== selectedSlug) {
      setSelectedSlug(activeSlug);
    }
  }, [activeSlug, selectedSlug]);

  useEffect(() => {
    const targetId = location.hash.slice(1);
    if (!targetId || !trackedAssets.length) return;
    const frame = window.requestAnimationFrame(() => document.getElementById(targetId)?.scrollIntoView({ block: "center" }));
    return () => window.cancelAnimationFrame(frame);
  }, [location.hash, trackedAssets]);

  const slugs = trackedAssets.map((asset) => asset.slug);
  const quotes = useQuery({
    queryKey: ["home-quotes", slugs],
    queryFn: () => getQuotes(slugs),
    enabled: canLoadMarket && hasMachineReadableMarketData && slugs.length > 0,
    refetchInterval: 60_000,
    refetchOnWindowFocus: "always",
    refetchOnReconnect: "always",
  });
  useEffect(() => {
    if (!quotes.dataUpdatedAt) return;
    const interval = window.setInterval(() => setFreshnessClock(Date.now()), 1_000);
    return () => window.clearInterval(interval);
  }, [quotes.dataUpdatedAt]);
  const freshnessElapsedSeconds = quotes.dataUpdatedAt
    ? Math.max(0, (freshnessClock - quotes.dataUpdatedAt) / 1_000)
    : 0;
  const candles = useQuery({
    queryKey: ["home-candles", activeSlug, timeframe],
    queryFn: async () => {
      const response = await getCandles(activeSlug, timeframe);
      if (response.timeframe !== timeframe) {
        throw new Error("Candle timeframe mismatch");
      }
      return { ...response, items: normalizeCandles(response.items) };
    },
    enabled: canLoadMarket && hasMachineReadableMarketData && Boolean(activeSlug),
    refetchOnWindowFocus: "always",
    refetchOnReconnect: "always",
  });

  if (state === "idle" || state === "validating") return <DashboardSkeleton />;
  if (!canLoadMarket) {
    return (
      <BlockingState
        title="Откройте Pepe через Telegram"
        message={state === "browser"
          ? "Telegram не завершил инициализацию Mini App. Закройте окно и откройте приложение снова."
          : "Не удалось подтвердить запуск через Telegram. Закройте окно и откройте приложение снова."}
        diagnosticCode={diagnosticCode ?? (
          telegramInitState === "TG_INIT_TIMEOUT" ? "TG_INIT_TIMEOUT" : "AUTH_EXCHANGE_FAILED"
        )}
      />
    );
  }
  if (capabilities.isLoading) return <DashboardSkeleton />;
  if (capabilities.isError) {
    return <BlockingState title="Не удалось определить доступность рыночных данных" message="Проверьте подключение и повторите запрос." retry={() => void capabilities.refetch()} />;
  }
  if (!hasMachineReadableMarketData && capabilities.data?.mode !== "embedded") {
    return <BlockingState title="Рыночные данные недоступны" message="Внешний источник графика ещё не настроен. Числовые котировки и свечи сейчас не отображаются." />;
  }
  if (catalog.isLoading) return <DashboardSkeleton />;
  if (catalog.isError) {
    return (
      <BlockingState
        title="Не удалось загрузить рынок"
        message="Проверьте подключение и повторите запрос."
        diagnosticCode={marketDiagnosticCode(catalog.error)}
        retry={() => void catalog.refetch()}
      />
    );
  }
  if (trackedAssets.length === 0) {
    return <BlockingState title="Инструменты пока недоступны" message="Каталог не содержит активных рыночных инструментов." retry={() => void catalog.refetch()} />;
  }

  const selected = selectedAsset;
  if (!selected) {
    return <BlockingState title="Инструменты пока недоступны" message="Каталог не содержит активных рыночных инструментов." retry={() => void catalog.refetch()} />;
  }
  if (!hasMachineReadableMarketData) {
    return (
      <main className="market-home">
        <header className="home-header safe-area-top">
          <div><span className="section-kicker">Market intelligence</span><h1>Pepe</h1></div>
          <span className="home-status"><i />Secure · <small aria-label="Сборка Mini App">{BUILD_ID}</small></span>
        </header>
        <section className="chart-card">
          <div className="chart-toolbar" role="group" aria-label="Инструмент">
            {trackedAssets.map((asset) => <button key={asset.slug} type="button" aria-pressed={asset.slug === selected.slug} onClick={() => setSelectedSlug(asset.slug)}>{asset.symbol}</button>)}
          </div>
          <div className="chart-toolbar" role="group" aria-label="Таймфрейм">
            {TIMEFRAMES.map((value) => <button key={value} type="button" aria-pressed={timeframe === value} onClick={() => setTimeframe(value)}>{value}</button>)}
          </div>
        </section>
        <EmbeddedMarketChart state="provider-not-configured" />
      </main>
    );
  }
  const selectedQuote = quotes.data?.items.find((quote) => quote.slug === selected.slug);
  const selectedFreshness = selectedQuote
    ? quoteFreshness(selectedQuote, freshnessElapsedSeconds)
    : null;
  const stats = candleStatistics(candles.data?.items ?? []);
  const quoteUnavailable = quotes.data?.unavailable.includes(selected.slug) ?? false;

  return (
    <main className="market-home">
      <header className="home-header safe-area-top">
        <div><span className="section-kicker">Market intelligence</span><h1>Pepe</h1></div>
        <span className="home-status">
          <i />Secure · <small aria-label="Сборка Mini App">{BUILD_ID}</small>
        </span>
      </header>
      <HeroCard asset={selected} quote={selectedQuote} freshnessElapsedSeconds={freshnessElapsedSeconds} stats={stats} timeframe={timeframe} loading={quotes.isLoading} unavailable={quoteUnavailable} error={quotes.isError} onRetry={() => void quotes.refetch()} />
      <QuickActions />
      <DataContext quote={selectedQuote} freshnessElapsedSeconds={freshnessElapsedSeconds} />
      {quotes.isError ? (
        <section className="inline-error" role="alert"><AlertTriangle size={17} /><span>Не удалось обновить котировки</span><button type="button" onClick={() => void quotes.refetch()}>Повторить загрузку</button></section>
      ) : null}
      <MarketFeed assets={trackedAssets} quotes={quotes.data?.items ?? []} freshnessElapsedSeconds={freshnessElapsedSeconds} unavailable={quotes.data?.unavailable ?? []} notFound={quotes.data?.not_found ?? []} selectedSlug={selected.slug} onSelect={setSelectedSlug} />
      <ChartCard assets={trackedAssets} selected={selected} selectedSlug={selected.slug} onSelect={setSelectedSlug} timeframe={timeframe} onTimeframe={setTimeframe} candles={candles.data} loading={candles.isLoading} error={candles.isError} retry={() => void candles.refetch()} />
      <InformationCards asset={selected} />
      {selectedFreshness?.stale ? <div className="stale-notice" role="status"><Activity size={15} />Данные устарели — показано последнее подтверждённое значение.</div> : null}
    </main>
  );
}
