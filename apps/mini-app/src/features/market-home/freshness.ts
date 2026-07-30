import type { Quote } from "@/shared/api/market";

export interface QuoteFreshness {
  text: string;
  stale: boolean;
}

export function quoteFreshness(quote: Quote, elapsedSeconds: number): QuoteFreshness {
  const safeElapsedSeconds = Number.isFinite(elapsedSeconds) ? Math.max(0, elapsedSeconds) : 0;
  const ageSeconds = Math.max(0, quote.age_seconds + safeElapsedSeconds);
  const threshold = Number.isFinite(quote.stale_after_seconds) && quote.stale_after_seconds > 0
    ? quote.stale_after_seconds
    : 0;
  const stale = quote.data_status === "stale" || (threshold > 0 && ageSeconds >= threshold);

  if (quote.data_status === "stale") return { text: "данные устарели", stale };
  if (ageSeconds < 5) return { text: "только что", stale };
  if (ageSeconds < 60) return { text: `${Math.floor(ageSeconds)} сек назад`, stale };
  return { text: `${Math.floor(ageSeconds / 60)} мин назад`, stale };
}
