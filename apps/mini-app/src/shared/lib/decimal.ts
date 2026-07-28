import type { Candle } from "@/shared/api/market";

const DECIMAL_PATTERN = /^([+-]?)(\d+)(?:\.(\d+))?$/;

function decimalParts(value: string) {
  const match = DECIMAL_PATTERN.exec(value);
  if (!match) throw new Error(`Invalid decimal value: ${value}`);
  return {
    negative: match[1] === "-",
    whole: match[2] ?? "0",
    fraction: match[3] ?? "",
  };
}

export function decimalScale(value: string): number {
  return decimalParts(value).fraction.length;
}

export function decimalToScaled(value: string, scale: number): bigint {
  const { negative, whole, fraction } = decimalParts(value);
  if (fraction.length > scale) {
    throw new Error(`Scale ${scale} is too small for ${value}`);
  }
  const digits = `${whole}${fraction.padEnd(scale, "0")}`.replace(/^0+/, "") || "0";
  return (negative ? -1n : 1n) * BigInt(digits);
}

export function scaledToDecimal(value: bigint, scale: number): string {
  const negative = value < 0n;
  const digits = (negative ? -value : value).toString().padStart(scale + 1, "0");
  const whole = scale === 0 ? digits : digits.slice(0, -scale);
  const fraction = scale === 0 ? "" : digits.slice(-scale);
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

export function formatDecimal(value: string, maxFractionDigits = 8): string {
  const { negative, whole, fraction } = decimalParts(value);
  const groupedWhole = whole.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const visibleFraction = fraction.slice(0, maxFractionDigits).replace(/0+$/, "");
  return `${negative ? "−" : ""}${groupedWhole}${visibleFraction ? `.${visibleFraction}` : ""}`;
}

export function formatSignedDecimal(value: string, maxFractionDigits = 8): string {
  const formatted = formatDecimal(value, maxFractionDigits);
  const isZero = decimalToScaled(value, decimalScale(value)) === 0n;
  if (isZero || formatted.startsWith("−")) return formatted;
  return `+${formatted}`;
}

export interface CandleStatistics {
  high: string;
  low: string;
  average: string;
  range: string;
}

export function candleStatistics(candles: Candle[]): CandleStatistics | null {
  if (candles.length === 0) return null;
  const scale = candles.reduce(
    (maximum, candle) => Math.max(
      maximum,
      decimalScale(candle.high),
      decimalScale(candle.low),
      decimalScale(candle.close),
    ),
    0,
  );
  const highs = candles.map((candle) => decimalToScaled(candle.high, scale));
  const lows = candles.map((candle) => decimalToScaled(candle.low, scale));
  const closes = candles.map((candle) => decimalToScaled(candle.close, scale));
  const high = highs.reduce((current, value) => value > current ? value : current);
  const low = lows.reduce((current, value) => value < current ? value : current);
  const average = closes.reduce((total, value) => total + value, 0n) / BigInt(closes.length);

  return {
    high: scaledToDecimal(high, scale),
    low: scaledToDecimal(low, scale),
    average: scaledToDecimal(average, scale),
    range: scaledToDecimal(high - low, scale),
  };
}
