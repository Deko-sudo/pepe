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
import { BUILD_ID, type DiagnosticCode } from "@/shared/diagnostics";

import { TelegramAuthContext, TelegramContext } from "./context";
import { createBrowserBridge, createTelegramBridgeIfAvailable } from "./factory";
import type { TelegramAuthState, TelegramBridge, TelegramInitState } from "./types";

interface TelegramProviderProps {
  children: React.ReactNode;
}

export const TELEGRAM_INIT_RETRY_INTERVAL_MS = 50;
export const TELEGRAM_INIT_TIMEOUT_MS = 1500;

export function TelegramProvider({ children }: TelegramProviderProps) {
  const [bridge, setBridge] = useState<TelegramBridge | null>(null);
  const [telegramInitState, setTelegramInitState] = useState<TelegramInitState>(
    "TG_INIT_WAITING",
  );
  const [state, setState] = useState<TelegramValidationState>("idle");
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [diagnosticCode, setDiagnosticCode] = useState<DiagnosticCode | null>(null);
  const bootstrapPromise = useRef<Promise<void> | null>(null);

  useEffect(() => {
    let candidate: TelegramBridge | null = null;
    let settled = false;
    let retryTimer: number | undefined;
    let timeoutTimer: number | undefined;

    const stopTimers = () => {
      if (retryTimer !== undefined) window.clearInterval(retryTimer);
      if (timeoutTimer !== undefined) window.clearTimeout(timeoutTimer);
    };

    const probe = (): boolean => {
      if (!candidate) {
        candidate = createTelegramBridgeIfAvailable();
        if (candidate) {
          candidate.ready();
          candidate.expand();
        }
      }
      if (!candidate?.getInitData()) return false;

      settled = true;
      stopTimers();
      setTelegramInitState("TG_READY");
      setBridge(candidate);
      return true;
    };

    if (!probe()) {
      retryTimer = window.setInterval(probe, TELEGRAM_INIT_RETRY_INTERVAL_MS);
      timeoutTimer = window.setTimeout(() => {
        if (settled) return;
        settled = true;
        stopTimers();
        setTelegramInitState("TG_INIT_TIMEOUT");
        setBridge(candidate ?? createBrowserBridge());
      }, TELEGRAM_INIT_TIMEOUT_MS);
    }

    return () => {
      settled = true;
      stopTimers();
    };
  }, []);

  const bootstrap = useCallback(() => {
    if (!bridge) return Promise.resolve();
    if (bootstrapPromise.current) {
      return bootstrapPromise.current;
    }

    const pendingBootstrap = (async () => {
      setState("validating");
      setError(null);
      setDiagnosticCode(null);

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
          setDiagnosticCode("AUTH_EXCHANGE_FAILED");
          return;
        }
      }

      const initData = bridge.getInitData();
      if (!initData) {
        setUser(null);
        setState("browser");
        setDiagnosticCode(
          telegramInitState === "TG_INIT_TIMEOUT" ? "TG_INIT_TIMEOUT" : "TG_INIT_UNAVAILABLE",
        );
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
        setDiagnosticCode(
          exchangeError instanceof ApiError && exchangeError.code === "SESSION_HEADER_MISSING"
            ? "SESSION_HEADER_MISSING"
            : "AUTH_EXCHANGE_FAILED",
        );
      }
    })();

    bootstrapPromise.current = pendingBootstrap;
    void pendingBootstrap.finally(() => {
      if (bootstrapPromise.current === pendingBootstrap) {
        bootstrapPromise.current = null;
      }
    });
    return pendingBootstrap;
  }, [bridge, telegramInitState]);

  const endSession = useCallback(async (request: () => Promise<void>) => {
    try {
      await request();
      setUser(null);
      setState("idle");
      setError(null);
      setDiagnosticCode(null);
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
    if (bridge) void bootstrap();
  }, [bootstrap, bridge]);

  const authContext: TelegramAuthState = useMemo(
    () => ({ state, telegramInitState, user, error, diagnosticCode, logout, logoutAll }),
    [diagnosticCode, error, logout, logoutAll, state, telegramInitState, user],
  );

  if (!bridge) {
    return (
      <main className="state-shell">
        <section className="state-card" role="status">
          <h1>Подключаем Telegram</h1>
          <p>Ожидаем безопасную инициализацию Mini App.</p>
          <p className="state-diagnostic">Код: TG_INIT_WAITING · Сборка: {BUILD_ID}</p>
        </section>
      </main>
    );
  }

  return (
    <>
      <span className="sr-only">Состояние Telegram: {telegramInitState}</span>
      <TelegramContext.Provider value={bridge}>
        <TelegramAuthContext.Provider value={authContext}>
          {children}
        </TelegramAuthContext.Provider>
      </TelegramContext.Provider>
    </>
  );
}
