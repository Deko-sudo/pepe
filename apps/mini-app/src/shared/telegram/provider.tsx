import React, { createContext, useContext, useMemo } from "react";
import type { TelegramBridge } from "./types";
import { createTelegramBridge } from "./factory";

const TelegramContext = createContext<TelegramBridge | null>(null);

interface TelegramProviderProps {
  children: React.ReactNode;
}

export function TelegramProvider({ children }: TelegramProviderProps) {
  const bridge = useMemo(() => createTelegramBridge(), []);

  return (
    <TelegramContext.Provider value={bridge}>{children}</TelegramContext.Provider>
  );
}

export function useTelegram(): TelegramBridge {
  const ctx = useContext(TelegramContext);
  if (!ctx) {
    throw new Error("useTelegram must be used within TelegramProvider");
  }
  return ctx;
}
