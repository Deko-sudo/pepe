import React, { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, exchangeTelegramSession, getCurrentUser } from "@/shared/api";
import type { TelegramUser, TelegramValidationState } from "@/shared/api";

import { TelegramAuthContext, TelegramContext } from "./context";
import { createTelegramBridge } from "./factory";
import type { TelegramAuthState } from "./types";

interface TelegramProviderProps {
  children: React.ReactNode;
}

export function TelegramProvider({ children }: TelegramProviderProps) {
  const bridge = useMemo(() => createTelegramBridge(), []);
  const [state, setState] = useState<TelegramValidationState>("idle");
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  const bootstrap = useCallback(async () => {
    setState("validating");
    setError(null);

    try {
      const sessionUser = await getCurrentUser();
      setUser(sessionUser);
      setState("valid");
      return;
    } catch (sessionError) {
      if (!(sessionError instanceof ApiError) || sessionError.status !== 401) {
        setUser(null);
        if (sessionError instanceof ApiError && sessionError.status === 503) {
          setState("unavailable");
          setError("Проверка Telegram временно недоступна.");
        } else {
          setState("invalid");
          setError("Не удалось восстановить сессию.");
        }
        return;
      }
    }

    const initData = bridge.getInitData();
    if (!initData) {
      setUser(null);
      setState("browser");
      return;
    }

    try {
      const sessionUser = await exchangeTelegramSession(initData);
      setUser(sessionUser);
      setState("valid");
    } catch (exchangeError) {
      setUser(null);
      if (exchangeError instanceof ApiError && exchangeError.status === 503) {
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
    void bootstrap();
  }, [bootstrap]);

  const authContext: TelegramAuthState = useMemo(
    () => ({ state, user, error }),
    [error, state, user],
  );

  return (
    <TelegramContext.Provider value={bridge}>
      <TelegramAuthContext.Provider value={authContext}>
        {children}
      </TelegramAuthContext.Provider>
    </TelegramContext.Provider>
  );
}
