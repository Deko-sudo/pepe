import type { Quote } from "@/shared/api/market";

const CLIENT_STALE_AFTER_SECONDS = 60;

export interface QuoteFreshness {
  text: string;
  stale: boolean;
}

export function quoteFreshness(quote: Quote, elapsedSeconds: number): QuoteFreshness {
  const safeElapsedSeconds = Number.isFinite(elapsedSeconds) ? Math.max(0, elapsedSeconds) : 0;
  const ageSeconds = Math.max(0, quote.age_seconds + safeElapsedSeconds);
  const stale = quote.data_status === "stale" || ageSeconds >= CLIENT_STALE_AFTER_SECONDS;

  if (quote.data_status === "stale") return { text: "данные устарели", stale };
  if (ageSeconds < 5) return { text: "только что", stale };
  if (ageSeconds < 60) return { text: `${Math.floor(ageSeconds)} сек назад`, stale };
  return { text: `${Math.floor(ageSeconds / 60)} мин назад`, stale };
}
