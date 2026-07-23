import React, { useMemo } from "react";
import { createTelegramBridge } from "./factory";
import { TelegramContext } from "./context";

interface TelegramProviderProps {
  children: React.ReactNode;
}

export function TelegramProvider({ children }: TelegramProviderProps) {
  const bridge = useMemo(() => createTelegramBridge(), []);

  return (
    <TelegramContext.Provider value={bridge}>{children}</TelegramContext.Provider>
  );
}
