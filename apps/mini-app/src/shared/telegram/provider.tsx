import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  ApiError,
  activateSessionToken,
  clearSessionToken,
  exchangeTelegramSession,
  getCurrentUser,
  logout as logoutRequest,
  logoutAll as logoutAllRequest,
} from "@/shared/api";
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
  const bootstrapPromise = useRef<Promise<void> | null>(null);

  const bootstrap = useCallback(() => {
    if (bootstrapPromise.current) {
      return bootstrapPromise.current;
    }

    const pendingBootstrap = (async () => {
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
        clearSessionToken();
        const exchange = await exchangeTelegramSession(
          initData,
          bridge.requiresSessionHeaderFallback(),
        );
        let sessionUser: TelegramUser;
        try {
          sessionUser = await getCurrentUser();
        } catch (cookieError) {
          if (!(cookieError instanceof ApiError) || cookieError.status !== 401) {
            throw cookieError;
          }
          const fallbackToken = exchange.sessionToken;
          if (!fallbackToken) {
            throw cookieError;
          }
          activateSessionToken(fallbackToken);
          try {
            sessionUser = await getCurrentUser();
          } catch (headerError) {
            clearSessionToken();
            throw headerError;
          }
        }
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
    })();

    bootstrapPromise.current = pendingBootstrap;
    void pendingBootstrap.finally(() => {
      if (bootstrapPromise.current === pendingBootstrap) {
        bootstrapPromise.current = null;
      }
    });
    return pendingBootstrap;
  }, [bridge]);

  const endSession = useCallback(async (request: () => Promise<void>) => {
    try {
      await request();
      setUser(null);
      setState("idle");
      setError(null);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError ? requestError.message : "Не удалось завершить сессию.",
      );
      throw requestError;
    }
  }, []);

  const logout = useCallback(() => endSession(logoutRequest), [endSession]);
  const logoutAll = useCallback(() => endSession(logoutAllRequest), [endSession]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const authContext: TelegramAuthState = useMemo(
    () => ({ state, user, error, logout, logoutAll }),
    [error, logout, logoutAll, state, user],
  );

  return (
    <TelegramContext.Provider value={bridge}>
      <TelegramAuthContext.Provider value={authContext}>
        {children}
      </TelegramAuthContext.Provider>
    </TelegramContext.Provider>
  );
}
