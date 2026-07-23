import React, { useMemo, useState, useEffect, useCallback } from "react";
import { createTelegramBridge } from "./factory";
import { TelegramContext, TelegramAuthContext } from "./context";
import type { TelegramAuthState } from "./types";
import { validateTelegramInitData, ApiError } from "@/shared/api";
import type { TelegramUser, TelegramValidationState } from "@/shared/api";

interface TelegramProviderProps {
  children: React.ReactNode;
}

export function TelegramProvider({ children }: TelegramProviderProps) {
  const bridge = useMemo(() => createTelegramBridge(), []);

  const [state, setState] = useState<TelegramValidationState>("idle");
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  const validate = useCallback(async () => {
    const initData = bridge.getInitData();

    if (!initData) {
      setState("browser");
      return;
    }

    setState("validating");
    setError(null);

    try {
      const result = await validateTelegramInitData(initData);
      setUser(result.user);
      setState("valid");
    } catch (err) {
      setUser(null);
      if (err instanceof ApiError && err.status === 503) {
        setState("unavailable");
        setError("Проверка Telegram временно недоступна.");
      } else {
        setState("invalid");
        setError(
          "Не удалось подтвердить запуск через Telegram. Закройте приложение и откройте его снова.",
        );
      }
    }
  }, [bridge]);

  useEffect(() => {
    validate();
  }, [validate]);

  const authContext: TelegramAuthState = useMemo(
    () => ({ state, user, error }),
    [state, user, error],
  );

  return (
    <TelegramContext.Provider value={bridge}>
      <TelegramAuthContext.Provider value={authContext}>
        {children}
      </TelegramAuthContext.Provider>
    </TelegramContext.Provider>
  );
}
