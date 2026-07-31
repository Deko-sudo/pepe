export type EmbeddedMarketChartState =
  | "capability-loading"
  | "capability-error"
  | "configuration-loading"
  | "provider-not-configured"
  | "configuration-disabled"
  | "unsupported-instrument"
  | "unsupported-timeframe"
  | "request-error"
  | "offline"
  | "future-content-loading"
  | "future-content-timeout"
  | "future-content-blocked"
  | "future-provider-unavailable";

const messages: Record<EmbeddedMarketChartState, string> = {
  "capability-loading": "Проверяем доступность графика…",
  "capability-error": "Не удалось определить доступность графика.",
  "configuration-loading": "Проверяем конфигурацию графика…",
  "provider-not-configured": "Источник встроенного графика ещё не настроен.",
  "configuration-disabled": "Встроенный график отключён.",
  "unsupported-instrument": "Для выбранного инструмента график пока недоступен.",
  "unsupported-timeframe": "Для выбранного таймфрейма график пока недоступен.",
  "request-error": "Не удалось подготовить график.",
  offline: "Нет подключения к сети. График будет доступен после восстановления соединения.",
  "future-content-loading": "График готовится к загрузке…",
  "future-content-timeout": "Загрузка графика заняла слишком много времени.",
  "future-content-blocked": "Браузер заблокировал загрузку графика.",
  "future-provider-unavailable": "Источник графика временно недоступен.",
};

export function EmbeddedMarketChart({ state, onRetry }: { state: EmbeddedMarketChartState; onRetry?: () => void }) {
  const isError = state.endsWith("error") || state.includes("unavailable") || state.includes("blocked") || state.includes("timeout");
  return <section className="card" aria-live="polite">
    <h2 className="text-sm font-medium text-text-secondary">Встроенный график</h2>
    <p className="mt-3 text-sm" role={isError ? "alert" : "status"}>{messages[state]}</p>
    {onRetry && isError ? <button className="mt-3 underline" type="button" onClick={onRetry}>Повторить</button> : null}
  </section>;
}
