import { z } from "zod";
import { DECIMAL_PATTERN } from "@/shared/lib/decimal";
import { ApiError } from "./client";
import { withSessionAuth } from "./session-token";

const API_BASE = "/api/v1";
const DecimalSchema = z.string().regex(DECIMAL_PATTERN);
const NullableDecimalSchema = DecimalSchema.nullable();

export const TimeframeSchema = z.enum(["1m", "5m", "15m", "1h", "4h", "1d"]);
export type Timeframe = z.infer<typeof TimeframeSchema>;
export const TIMEFRAMES: Timeframe[] = [...TimeframeSchema.options];

export const AssetSchema = z.object({
  id: z.string().uuid(), slug: z.string(), symbol: z.string(), display_name: z.string(),
  asset_class: z.string(), market_type: z.string(), base_asset: z.string().nullable(),
  quote_asset: z.string().nullable(), price_precision: z.number(), quantity_precision: z.number().nullable(),
  timezone: z.string(), calendar_kind: z.string(), trading_calendar: z.string(), metadata_version: z.number(), is_enabled: z.boolean(),
});
export type Asset = z.infer<typeof AssetSchema>;
export const CatalogSchema = z.object({ items: z.array(AssetSchema), next_cursor: z.string().nullable() });

export const QuoteSchema = z.object({
  slug: z.string(), price: DecimalSchema, bid: NullableDecimalSchema, ask: NullableDecimalSchema, mid: NullableDecimalSchema,
  open_24h: NullableDecimalSchema, high_24h: NullableDecimalSchema, low_24h: NullableDecimalSchema,
  change_24h: NullableDecimalSchema, change_percent_24h: NullableDecimalSchema,
  base_volume_24h: NullableDecimalSchema, quote_volume_24h: NullableDecimalSchema,
  market_status: z.string(), data_status: z.string(), observed_at: z.string(), received_at: z.string(), age_seconds: z.number(),
  stale_after_seconds: z.number(),
  provenance: z.object({ source_label: z.string(), venue_label: z.string().nullable(), market_type: z.string(), price_type: z.string(), delay_class: z.string() }),
}).passthrough();
export type Quote = z.infer<typeof QuoteSchema>;
export const QuoteBatchSchema = z.object({ items: z.array(QuoteSchema), unavailable: z.array(z.string()), not_found: z.array(z.string()) });

export const CandleSchema = z.object({
  open_time: z.string(), close_time: z.string(), open: DecimalSchema, high: DecimalSchema, low: DecimalSchema, close: DecimalSchema,
  base_volume: NullableDecimalSchema, quote_volume: NullableDecimalSchema, trade_count: z.number().int().nullable(),
  source_label: z.string(), venue_label: z.string().nullable(), received_at: z.string(),
}).passthrough();
export type Candle = z.infer<typeof CandleSchema>;
export const CandlesSchema = z.object({ timeframe: TimeframeSchema, items: z.array(CandleSchema) });

export const MarketDataCapabilitiesSchema = z.object({
  contract_version: z.literal("v1"),
  mode: z.enum(["demo", "embedded", "live", "unavailable"]),
  status: z.enum(["available", "unavailable"]),
  numeric_quotes_available: z.boolean(),
  server_candles_available: z.boolean(),
  embedded_chart_available: z.boolean(),
  analytics_available: z.boolean(),
  quote_cards_visible: z.boolean(),
  unavailable_reason_code: z.string().nullable(),
});
export type MarketDataCapabilities = z.infer<typeof MarketDataCapabilitiesSchema>;


async function request<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  let response: Response;
  try { response = await fetch(`${API_BASE}${path}`, withSessionAuth()); }
  catch { throw new ApiError("Network request failed", 0); }
  if (!response.ok) throw new ApiError(`HTTP ${response.status}`, response.status);
  return schema.parse(await response.json());
}
export const getAssets = () => request("/assets?limit=100", CatalogSchema);
export const getMarketDataCapabilities = () => request("/market-data/capabilities", MarketDataCapabilitiesSchema);

export const getQuotes = (slugs: string[]) => {
  const query = slugs.map((slug) => `slug=${encodeURIComponent(slug)}`).join("&");
  return request(`/assets/quotes?${query}`, QuoteBatchSchema);
};
export const getQuote = (slug: string) => getQuotes([slug]);
export const getCandles = (slug: string, timeframe: Timeframe) => request(`/market-data/instruments/${encodeURIComponent(slug)}/candles?timeframe=${timeframe}&limit=120`, CandlesSchema);
