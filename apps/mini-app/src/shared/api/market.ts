import { z } from "zod";
import { ApiError } from "./client";

const API_BASE = "/api/v1";

export const TimeframeSchema = z.enum(["1m", "5m", "15m", "1h", "4h", "1d"]);
export type Timeframe = z.infer<typeof TimeframeSchema>;

export const AssetSchema = z.object({
  id: z.string().uuid(), slug: z.string(), symbol: z.string(), display_name: z.string(),
  asset_class: z.string(), market_type: z.string(), base_asset: z.string().nullable(),
  quote_asset: z.string().nullable(), price_precision: z.number(), quantity_precision: z.number().nullable(),
  timezone: z.string(), calendar_kind: z.string(), trading_calendar: z.string(), metadata_version: z.number(), is_enabled: z.boolean(),
});
export type Asset = z.infer<typeof AssetSchema>;
export const CatalogSchema = z.object({ items: z.array(AssetSchema), next_cursor: z.string().nullable() });

export const QuoteSchema = z.object({
  slug: z.string(), price: z.string(), bid: z.string().nullable(), ask: z.string().nullable(), mid: z.string().nullable(),
  market_status: z.string(), data_status: z.string(), observed_at: z.string(), received_at: z.string(), age_seconds: z.number(),
  provenance: z.object({ source_label: z.string(), venue_label: z.string().nullable(), market_type: z.string(), price_type: z.string(), delay_class: z.string() }),
}).passthrough();
export type Quote = z.infer<typeof QuoteSchema>;
export const QuoteBatchSchema = z.object({ items: z.array(QuoteSchema), unavailable: z.array(z.string()), not_found: z.array(z.string()) });

export const CandleSchema = z.object({ open_time: z.string(), close_time: z.string(), open: z.string(), high: z.string(), low: z.string(), close: z.string(), source_label: z.string(), venue_label: z.string().nullable(), received_at: z.string() }).passthrough();
export type Candle = z.infer<typeof CandleSchema>;
export const CandlesSchema = z.object({ timeframe: TimeframeSchema, items: z.array(CandleSchema) });

async function request<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  let response: Response;
  try { response = await fetch(`${API_BASE}${path}`, { credentials: "include" }); }
  catch { throw new ApiError("Network request failed", 0); }
  if (!response.ok) throw new ApiError(`HTTP ${response.status}`, response.status);
  return schema.parse(await response.json());
}
export const getAssets = () => request("/assets?limit=100", CatalogSchema);
export const getQuote = (slug: string) => request(`/assets/quotes?slug=${encodeURIComponent(slug)}`, QuoteBatchSchema);
export const getCandles = (slug: string, timeframe: Timeframe) => request(`/market-data/instruments/${encodeURIComponent(slug)}/candles?timeframe=${timeframe}&limit=120`, CandlesSchema);
