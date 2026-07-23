import { createContext, useContext } from "react";
import type { TelegramAuthState, TelegramBridge } from "./types";

export const TelegramContext = createContext<TelegramBridge | null>(null);

export const TelegramAuthContext = createContext<TelegramAuthState | null>(null);

export function useTelegram(): TelegramBridge {
  const ctx = useContext(TelegramContext);
  if (!ctx) {
    throw new Error("useTelegram must be used within TelegramProvider");
  }
  return ctx;
}

export function useTelegramAuth(): TelegramAuthState {
  const ctx = useContext(TelegramAuthContext);
  if (!ctx) {
    throw new Error("useTelegramAuth must be used within TelegramProvider");
  }
  return ctx;
}
