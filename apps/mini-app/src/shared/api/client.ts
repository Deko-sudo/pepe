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

async function parseErrorDetail(response: Response): Promise<string | null> {
  try {
    const data: unknown = await response.json();

    if (
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof data.detail === "string"
    ) {
      return data.detail;
    }
  } catch {
    return null;
  }

  return null;
}

export async function validateTelegramInitData(
  initData: string,
): Promise<TelegramValidateResponse> {
  const response = await fetch(`${API_BASE}/auth/telegram/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData }),
  });

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    throw new ApiError(detail ?? `HTTP ${response.status}`, response.status);
  }

  const data: unknown = await response.json();
  return TelegramValidateResponseSchema.parse(data);
}
