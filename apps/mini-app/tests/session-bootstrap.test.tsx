import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { clearSessionToken } from "../src/shared/api";
import { TelegramProvider } from "../src/shared/telegram/provider";
import { useTelegramAuth } from "../src/shared/telegram/context";

function installMockWebApp(initData: string, platform = "tdesktop") {
  const webApp = {
      ready: vi.fn(),
      expand: vi.fn(),
      initData,
      platform,
      colorScheme: "dark" as const,
      themeParams: {},
      BackButton: { show: vi.fn(), hide: vi.fn(), onClick: vi.fn(), offClick: vi.fn() },
      HapticFeedback: { impactOccurred: vi.fn(), notificationOccurred: vi.fn() },
      showAlert: vi.fn(),
  };
  (window as Record<string, unknown>).Telegram = { WebApp: webApp };
  return webApp;
}

function Status() {
  const { state, user, error, diagnosticCode, logout, logoutAll } = useTelegramAuth();
  return (
    <div>
      <span data-testid="status">{`${state}:${user?.first_name ?? ""}`}</span>
      <span data-testid="error">{error ?? ""}</span>
      <span data-testid="diagnostic">{diagnosticCode ?? ""}</span>
      <button onClick={() => void logout().catch(() => undefined)}>Logout</button>
      <button onClick={() => void logoutAll().catch(() => undefined)}>Logout all</button>
    </div>
  );
}

function renderProvider() {
  return render(
    <TelegramProvider>
      <Status />
    </TelegramProvider>,
  );
}

const profile = {
  id: "11111111-1111-1111-1111-111111111111",
  telegram_id: 1,
  first_name: "Test",
  created_at: "2026-07-24T00:00:00Z",
  updated_at: "2026-07-24T00:00:00Z",
};

afterEach(() => {
  clearSessionToken();
  cleanup();
  delete (window as Record<string, unknown>).Telegram;
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("session bootstrap", () => {
  it("calls Telegram.WebApp.ready when the bridge is available immediately", async () => {
    const webApp = installMockWebApp("signed-init-data");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(profile), { status: 200 }),
    );

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    expect(webApp.ready).toHaveBeenCalledOnce();
  });

  it("waits for Telegram.WebApp to appear before starting the auth exchange", async () => {
    vi.useFakeTimers();
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(profile), {
          status: 200,
          headers: { "X-Pepe-Session-Token": "desktop-session-token" },
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    renderProvider();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.getByText(/TG_INIT_WAITING/)).toBeInTheDocument();

    const webApp = installMockWebApp("signed-init-data");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(webApp.ready).toHaveBeenCalledOnce();
    expect(fetchSpy).toHaveBeenCalled();
    expect(screen.getByTestId("status")).toHaveTextContent("valid:Test");
  });

  it("waits for initData that appears after Telegram.WebApp.ready()", async () => {
    vi.useFakeTimers();
    let initData = "";
    const webApp = installMockWebApp("");
    Object.defineProperty(webApp, "initData", { configurable: true, get: () => initData });
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(profile), {
          status: 200,
          headers: { "X-Pepe-Session-Token": "desktop-session-token" },
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    renderProvider();
    expect(webApp.ready).toHaveBeenCalledOnce();
    expect(fetchSpy).not.toHaveBeenCalled();

    initData = "signed-init-data";
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(screen.getByTestId("status")).toHaveTextContent("valid:Test");
    expect(fetchSpy).toHaveBeenCalledTimes(3);
  });

  it("uses the browser fallback only after the bounded Telegram timeout", async () => {
    vi.useFakeTimers();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 401 }),
    );

    renderProvider();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.getByText(/TG_INIT_WAITING/)).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(screen.getByTestId("status")).toHaveTextContent("browser:");
    expect(screen.getByTestId("diagnostic")).toHaveTextContent("TG_INIT_TIMEOUT");
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("cleans up Telegram initialization timers on unmount", () => {
    vi.useFakeTimers();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 401 }));

    const view = renderProvider();
    expect(vi.getTimerCount()).toBeGreaterThan(0);

    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("uses an existing cookie session before Telegram exchange", async () => {
    installMockWebApp("signed-init-data");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(profile), { status: 200 }),
    );

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/users/me",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("exchanges Telegram initData only after a 401 session check", async () => {
    installMockWebApp("signed-init-data");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(profile), {
          status: 200,
          headers: { "X-Pepe-Session-Token": "desktop-session-token" },
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    expect(fetchSpy).toHaveBeenNthCalledWith(1, "/api/v1/users/me", expect.any(Object));
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "/api/v1/auth/telegram/session",
      expect.objectContaining({ credentials: "include" }),
    );
    const exchangeHeaders = new Headers(fetchSpy.mock.calls[1][1]?.headers);
    expect(exchangeHeaders.get("X-Pepe-Session-Fallback")).toBe("telegram-desktop");
  });

  it("does not request the bearer fallback on Telegram Android", async () => {
    installMockWebApp("signed-init-data", "android");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    const exchangeHeaders = new Headers(fetchSpy.mock.calls[1][1]?.headers);
    expect(exchangeHeaders.has("X-Pepe-Session-Fallback")).toBe(false);
  });

  it("activates a header session when Telegram Desktop rejects the cookie", async () => {
    installMockWebApp("signed-init-data");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(profile), {
          status: 200,
          headers: { "X-Pepe-Session-Token": "desktop-session-token" },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    expect(fetchSpy.mock.calls[3][0]).toBe("/api/v1/users/me");
    const fallbackHeaders = new Headers(fetchSpy.mock.calls[3][1]?.headers);
    expect(fallbackHeaders.get("Authorization")).toBe("Bearer desktop-session-token");
  });

  it("classifies a missing Telegram Desktop session header safely", async () => {
    installMockWebApp("signed-init-data");
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("invalid:"));
    expect(screen.getByTestId("diagnostic")).toHaveTextContent("SESSION_HEADER_MISSING");
    expect(screen.getByTestId("error")).toHaveTextContent(
      "Не удалось подтвердить запуск через Telegram.",
    );
  });

  it("keeps browser mode controlled after an unauthenticated session check", async () => {
    vi.useFakeTimers();
    installMockWebApp("");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }));

    renderProvider();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    expect(screen.getByTestId("status")).toHaveTextContent("browser:");
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("clears auth state only after a successful logout", async () => {
    installMockWebApp("signed-init-data");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("idle:"));
    expect(screen.getByTestId("error")).toHaveTextContent("");
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "/api/v1/auth/logout",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("clears auth state only after a successful logout-all", async () => {
    installMockWebApp("signed-init-data");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    fireEvent.click(screen.getByRole("button", { name: "Logout all" }));

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("idle:"));
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "/api/v1/auth/logout-all",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("preserves the confirmed user when logout fails", async () => {
    installMockWebApp("signed-init-data");
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Forbidden." }), { status: 403 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => expect(screen.getByTestId("error")).toHaveTextContent("Forbidden."));
    expect(screen.getByTestId("status")).toHaveTextContent("valid:Test");
  });

  it("runs one bootstrap exchange in React StrictMode", async () => {
    installMockWebApp("signed-init-data");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(profile), {
          status: 200,
          headers: { "X-Pepe-Session-Token": "desktop-session-token" },
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    render(
      <React.StrictMode>
        <TelegramProvider>
          <Status />
        </TelegramProvider>
      </React.StrictMode>,
    );

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    expect(fetchSpy).toHaveBeenCalledTimes(3);
  });
});
