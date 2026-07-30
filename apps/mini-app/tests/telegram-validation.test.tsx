import { describe, expect, it, vi, afterEach } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";

import { ApiError, clearSessionToken, getCurrentUser } from "../src/shared/api";
import {
  TELEGRAM_INIT_TIMEOUT_MS,
  TelegramProvider,
} from "../src/shared/telegram/provider";
import { useTelegramAuth } from "../src/shared/telegram/context";

function installMockWebApp(initData: string) {
  (window as Record<string, unknown>).Telegram = {
    WebApp: {
      ready: vi.fn(),
      expand: vi.fn(),
      initData,
      colorScheme: "dark" as const,
      themeParams: {},
      BackButton: { show: vi.fn(), hide: vi.fn(), onClick: vi.fn(), offClick: vi.fn() },
      HapticFeedback: { impactOccurred: vi.fn(), notificationOccurred: vi.fn() },
      showAlert: vi.fn(),
    },
  };
}

function AuthStatus() {
  const { state, user, error } = useTelegramAuth();
  return (
    <div>
      <span data-testid="state">{state}</span>
      {user && <span data-testid="user">{user.first_name}</span>}
      {error && <span data-testid="error">{error}</span>}
    </div>
  );
}

function renderProvider() {
  return render(
    <TelegramProvider>
      <AuthStatus />
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
  delete (window as Record<string, unknown>).Telegram;
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("Telegram session bootstrap", () => {
  it("keeps browser mode after a 401 session check with no initData", async () => {
    vi.useFakeTimers();
    installMockWebApp("");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }));

    renderProvider();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(TELEGRAM_INIT_TIMEOUT_MS);
    });
    expect(screen.getByTestId("state")).toHaveTextContent("browser");
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("shows valid state after session exchange", async () => {
    installMockWebApp("signed-init-data");
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(profile), {
          status: 200,
          headers: { "X-Pepe-Session-Token": "desktop-session-token" },
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("user")).toHaveTextContent("Test"));
    expect(screen.getByTestId("state")).toHaveTextContent("valid");
  });

  it("shows unavailable state on exchange 503 response with HTML body", async () => {
    installMockWebApp("signed-init-data");
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response("<html>unavailable</html>", { status: 503 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("unavailable"));
  });

  it("does not store initData in browser storage", async () => {
    installMockWebApp("query_id=123&hash=abc");
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(profile), {
          status: 200,
          headers: { "X-Pepe-Session-Token": "desktop-session-token" },
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("valid"));
    if (typeof localStorage !== "undefined") {
      expect(localStorage.getItem("session") ?? "").not.toContain("query_id=123&hash=abc");
    }
    if (typeof sessionStorage !== "undefined") {
      expect(sessionStorage.getItem("session") ?? "").not.toContain("query_id=123&hash=abc");
    }
  });

  it("preserves status for empty session errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(null, { status: 503 }));

    await expect(getCurrentUser()).rejects.toMatchObject<ApiError>({ status: 503 });
  });
});
