import { describe, expect, it, vi } from "vitest";

import {
  ApiError,
  exchangeTelegramSession,
  getCurrentUser,
  logout,
  logoutAll,
} from "../src/shared/api";

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
        { status: 200 },
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
});
