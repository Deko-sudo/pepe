import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  activateSessionToken,
  clearSessionToken,
  exchangeTelegramSession,
  getCurrentUser,
  logout,
  logoutAll,
} from "../src/shared/api";

afterEach(() => {
  clearSessionToken();
  vi.restoreAllMocks();
});

describe("session API client", () => {
  it("uses credentials include for cookie-session calls", async () => {
    const profileResponse = () =>
      new Response(
        JSON.stringify({
          id: "11111111-1111-1111-1111-111111111111",
          telegram_id: 1,
          first_name: "Test",
          created_at: "2026-07-24T00:00:00Z",
          updated_at: "2026-07-24T00:00:00Z",
        }),
        {
          status: 200,
          headers: { "X-Pepe-Session-Token": "desktop-session-token" },
        },
      );
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(profileResponse);

    await getCurrentUser();
    await exchangeTelegramSession("signed-init-data");
    fetchSpy.mockResolvedValue(new Response(null, { status: 204 }));
    await logout();
    await logoutAll();

    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      "/api/v1/users/me",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "/api/v1/auth/telegram/session",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      3,
      "/api/v1/auth/logout",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      4,
      "/api/v1/auth/logout-all",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("uses an in-memory bearer token without browser persistence", async () => {
    const profile = {
      id: "11111111-1111-1111-1111-111111111111",
      telegram_id: 1,
      first_name: "Test",
      created_at: "2026-07-24T00:00:00Z",
      updated_at: "2026-07-24T00:00:00Z",
    };
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(profile), {
          status: 200,
          headers: { "X-Pepe-Session-Token": "desktop-session-token" },
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(profile), { status: 200 }));

    const exchange = await exchangeTelegramSession("signed-init-data");
    activateSessionToken(exchange.sessionToken);
    await getCurrentUser();

    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "/api/v1/users/me",
      expect.objectContaining({
        credentials: "include",
        headers: { Authorization: "Bearer desktop-session-token" },
      }),
    );
    clearSessionToken();
    await getCurrentUser();
    expect(fetchSpy).toHaveBeenNthCalledWith(
      3,
      "/api/v1/users/me",
      { credentials: "include" },
    );
  });

  it("classifies a successful exchange without the fallback header", async () => {
    const profile = {
      id: "11111111-1111-1111-1111-111111111111",
      telegram_id: 1,
      first_name: "Test",
      created_at: "2026-07-24T00:00:00Z",
      updated_at: "2026-07-24T00:00:00Z",
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(profile), { status: 200 }),
    );

    await expect(exchangeTelegramSession("signed-init-data")).rejects.toMatchObject<ApiError>({
      code: "SESSION_HEADER_MISSING",
    });
  });

  it("preserves status when an error body is empty or non-JSON", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(null, { status: 401 }));
    await expect(getCurrentUser()).rejects.toMatchObject<ApiError>({ status: 401 });

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("<html>forbidden</html>", { status: 403 }),
    );
    await expect(exchangeTelegramSession("signed-init-data")).rejects.toMatchObject<ApiError>({
      status: 403,
    });
  });

  it("does not access the HttpOnly session cookie from JavaScript", async () => {
    const originalDescriptor = Object.getOwnPropertyDescriptor(document, "cookie");
    const cookieGetter = vi.fn(() => {
      throw new Error("session cookie must not be read by JavaScript");
    });
    Object.defineProperty(document, "cookie", { configurable: true, get: cookieGetter });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));

    try {
      await logout();
      await logoutAll();
    } finally {
      if (originalDescriptor) {
        Object.defineProperty(document, "cookie", originalDescriptor);
      } else {
        Reflect.deleteProperty(document, "cookie");
      }
    }

    expect(cookieGetter).not.toHaveBeenCalled();
  });
});
