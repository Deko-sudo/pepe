import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { TelegramProvider } from "../src/shared/telegram/provider";
import { useTelegramAuth } from "../src/shared/telegram/context";

function installMockWebApp(initData?: string) {
  (window as Record<string, unknown>).Telegram = {
    WebApp: {
      ready: vi.fn(),
      expand: vi.fn(),
      initData: initData ?? "",
      colorScheme: "dark" as const,
      themeParams: {},
      BackButton: {
        show: vi.fn(),
        hide: vi.fn(),
        onClick: vi.fn(),
        offClick: vi.fn(),
      },
      HapticFeedback: {
        impactOccurred: vi.fn(),
        notificationOccurred: vi.fn(),
      },
      showAlert: vi.fn(),
    },
  };
}

function removeMockWebApp() {
  delete (window as Record<string, unknown>).Telegram;
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

function renderWithProviders() {
  return render(
    <BrowserRouter>
      <TelegramProvider>
        <AuthStatus />
      </TelegramProvider>
    </BrowserRouter>,
  );
}

describe("Telegram Validation - Browser Mode", () => {
  beforeEach(() => {
    removeMockWebApp();
    installMockWebApp("");
  });

  afterEach(() => {
    removeMockWebApp();
    vi.restoreAllMocks();
  });

  it("sets state to browser when no initData", async () => {
    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId("state").textContent).toBe("browser");
    });
  });

  it("does not make API request in browser mode", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId("state").textContent).toBe("browser");
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe("Telegram Validation - Telegram Mode", () => {
  beforeEach(() => {
    removeMockWebApp();
    installMockWebApp("query_id=123&user=%7B%7D&auth_date=123&hash=abc");
  });

  afterEach(() => {
    removeMockWebApp();
    vi.restoreAllMocks();
  });

  it("shows valid state on successful validation", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "valid",
          auth_date: 123,
          user: { telegram_id: 1, first_name: "Test" },
        }),
        { status: 200 },
      ),
    );

    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId("state").textContent).toBe("valid");
    });
    expect(screen.getByTestId("user").textContent).toBe("Test");
  });

  it("shows invalid state on 401 response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: "Не удалось подтвердить данные Telegram." }),
        { status: 401 },
      ),
    );

    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId("state").textContent).toBe("invalid");
    });
    expect(screen.getByTestId("error").textContent).toContain(
      "Не удалось подтвердить запуск через Telegram",
    );
  });

  it("shows unavailable state on 503 response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: "Проверка Telegram временно недоступна." }),
        { status: 503 },
      ),
    );

    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId("state").textContent).toBe("unavailable");
    });
  });
});

describe("Telegram Validation - Storage", () => {
  beforeEach(() => {
    removeMockWebApp();
    installMockWebApp("query_id=123&user=%7B%7D&auth_date=123&hash=abc");
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch {
      // jsdom may not support storage
    }
  });

  afterEach(() => {
    removeMockWebApp();
    vi.restoreAllMocks();
  });

  it("does not store initData in localStorage", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "valid",
          auth_date: 123,
          user: { telegram_id: 1, first_name: "Test" },
        }),
        { status: 200 },
      ),
    );

    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId("state").textContent).toBe("valid");
    });

    const keys = typeof localStorage !== "undefined" ? Object.keys(localStorage) : [];
    const hasInitData = keys.some(
      (k) => localStorage.getItem(k)?.includes("query_id") ?? false,
    );
    expect(hasInitData).toBe(false);
  });
});

describe("Telegram Validation - Zod Rejection", () => {
  beforeEach(() => {
    removeMockWebApp();
    installMockWebApp("query_id=123&user=%7B%7D&auth_date=123&hash=abc");
  });

  afterEach(() => {
    removeMockWebApp();
    vi.restoreAllMocks();
  });

  it("rejects malformed API response via Zod", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({ status: "unknown", data: "wrong" }),
        { status: 200 },
      ),
    );

    renderWithProviders();
    await waitFor(() => {
      expect(screen.getByTestId("state").textContent).toBe("invalid");
    });
  });
});
