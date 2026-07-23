import { createContext, useContext } from "react";
import type { TelegramBridge } from "./types";

export const TelegramContext = createContext<TelegramBridge | null>(null);

export function useTelegram(): TelegramBridge {
  const ctx = useContext(TelegramContext);
  if (!ctx) {
    throw new Error("useTelegram must be used within TelegramProvider");
  }
  return ctx;
}
