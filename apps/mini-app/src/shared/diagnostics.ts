import { ApiError } from "./api";

export type DiagnosticCode =
  | "TG_INIT_WAITING"
  | "TG_READY"
  | "TG_INIT_UNAVAILABLE"
  | "TG_INIT_TIMEOUT"
  | "AUTH_EXCHANGE_FAILED"
  | "SESSION_HEADER_MISSING"
  | "PROTECTED_API_401"
  | "PROTECTED_API_403"
  | "MARKET_API_FAILED";

const configuredBuildId = import.meta.env.VITE_BUILD_ID?.trim() ?? "";

export const BUILD_ID = /^[a-zA-Z0-9._-]{1,32}$/.test(configuredBuildId)
  ? configuredBuildId
  : "dev";

export function marketDiagnosticCode(error: unknown): DiagnosticCode {
  if (error instanceof ApiError) {
    if (error.status === 401) return "PROTECTED_API_401";
    if (error.status === 403) return "PROTECTED_API_403";
  }
  return "MARKET_API_FAILED";
}
