import { TelegramValidateResponseSchema } from "./types";
import type { TelegramValidateResponse } from "./types";

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

export async function validateTelegramInitData(
  initData: string,
): Promise<TelegramValidateResponse> {
  const response = await fetch(`${API_BASE}/auth/telegram/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(data.detail || "Validation failed", response.status);
  }

  return TelegramValidateResponseSchema.parse(data);
}
