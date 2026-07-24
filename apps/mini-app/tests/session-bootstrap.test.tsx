import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { TelegramProvider } from "../src/shared/telegram/provider";
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

function Status() {
  const { state, user, error, logout, logoutAll } = useTelegramAuth();
  return (
    <div>
      <span data-testid="status">{`${state}:${user?.first_name ?? ""}`}</span>
      <span data-testid="error">{error ?? ""}</span>
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

describe("session bootstrap", () => {
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
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    expect(fetchSpy).toHaveBeenNthCalledWith(1, "/api/v1/users/me", expect.any(Object));
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "/api/v1/auth/telegram/session",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("keeps browser mode controlled after an unauthenticated session check", async () => {
    installMockWebApp("");
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("browser:"));
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
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    render(
      <React.StrictMode>
        <TelegramProvider>
          <Status />
        </TelegramProvider>
      </React.StrictMode>,
    );

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("valid:Test"));
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });
});
