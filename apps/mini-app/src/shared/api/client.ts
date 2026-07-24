import {
  TelegramValidateResponseSchema,
  UserProfileSchema,
} from "./types";
import type { TelegramValidateResponse, UserProfile } from "./types";

const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
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
  const response = await fetch(`${API_BASE}/users/me`, { credentials: "include" });
  await requireSuccess(response);
  return UserProfileSchema.parse(await response.json());
}

export async function exchangeTelegramSession(initData: string): Promise<UserProfile> {
  const response = await fetch(`${API_BASE}/auth/telegram/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ init_data: initData }),
  });
  await requireSuccess(response);
  return UserProfileSchema.parse(await response.json());
}

async function endSession(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
  });
  await requireSuccess(response);
}

export async function logout(): Promise<void> {
  await endSession("/auth/logout");
}

export async function logoutAll(): Promise<void> {
  await endSession("/auth/logout-all");
}
