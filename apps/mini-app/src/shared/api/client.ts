import { TelegramValidateResponseSchema, UserProfileSchema } from "./types";
import type { TelegramValidateResponse, UserProfile } from "./types";
import { clearSessionToken, withSessionAuth } from "./session-token";

const API_BASE = "/api/v1";
const SESSION_TOKEN_HEADER = "X-Pepe-Session-Token";

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function parseErrorDetail(response: Response): Promise<string | null> {
  try {
    const data: unknown = await response.json();
    if (
      typeof data === "object"
      && data !== null
      && "detail" in data
      && typeof data.detail === "string"
    ) {
      return data.detail;
    }
  } catch {
    return null;
  }
  return null;
}

async function requireSuccess(response: Response): Promise<void> {
  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    throw new ApiError(detail ?? `HTTP ${response.status}`, response.status);
  }
}

export async function validateTelegramInitData(
  initData: string,
): Promise<TelegramValidateResponse> {
  const response = await fetch(`${API_BASE}/auth/telegram/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData }),
  });
  await requireSuccess(response);
  return TelegramValidateResponseSchema.parse(await response.json());
}

export async function getCurrentUser(): Promise<UserProfile> {
  const response = await fetch(`${API_BASE}/users/me`, withSessionAuth());
  await requireSuccess(response);
  return UserProfileSchema.parse(await response.json());
}

export async function exchangeTelegramSession(
  initData: string,
  requestHeaderFallback = false,
): Promise<{ user: UserProfile; sessionToken: string | null }> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (requestHeaderFallback) {
    headers.set("X-Pepe-Session-Fallback", "telegram-desktop");
  }
  const response = await fetch(`${API_BASE}/auth/telegram/session`, {
    method: "POST",
    headers,
    credentials: "include",
    body: JSON.stringify({ init_data: initData }),
  });
  await requireSuccess(response);
  const sessionToken = response.headers.get(SESSION_TOKEN_HEADER)?.trim() || null;
  if (requestHeaderFallback && !sessionToken) {
    throw new ApiError(
      "Session fallback header is missing.",
      response.status,
      "SESSION_HEADER_MISSING",
    );
  }
  return {
    user: UserProfileSchema.parse(await response.json()),
    sessionToken,
  };
}

async function endSession(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, withSessionAuth({
    method: "POST",
  }));
  await requireSuccess(response);
  clearSessionToken();
}

export async function logout(): Promise<void> {
  await endSession("/auth/logout");
}

export async function logoutAll(): Promise<void> {
  await endSession("/auth/logout-all");
}
