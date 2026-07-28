import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ─── Telegram WebApp mock setup ────────────────────────────────────

interface MockWebApp {
  ready: ReturnType<typeof vi.fn>;
  expand: ReturnType<typeof vi.fn>;
  initData: string;
  platform: string;
  colorScheme: "light" | "dark";
  themeParams: Record<string, string>;
  BackButton: {
    show: ReturnType<typeof vi.fn>;
    hide: ReturnType<typeof vi.fn>;
    onClick: ReturnType<typeof vi.fn>;
    offClick: ReturnType<typeof vi.fn>;
  };
  HapticFeedback: {
    impactOccurred: ReturnType<typeof vi.fn>;
    notificationOccurred: ReturnType<typeof vi.fn>;
  };
  showAlert: ReturnType<typeof vi.fn>;
}

function createMockWebApp(overrides?: Partial<MockWebApp>): MockWebApp {
  return {
    ready: vi.fn(),
    expand: vi.fn(),
    initData: "user=123&hash=abc123",
    platform: "tdesktop",
    colorScheme: "dark",
    themeParams: { bg_color: "#1a1a2e" },
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
    ...overrides,
  };
}

function installMockWebApp(mock: MockWebApp): void {
  (window as Record<string, unknown>).Telegram = { WebApp: mock };
}

function removeMockWebApp(): void {
  delete (window as Record<string, unknown>).Telegram;
}

// ─── Tests ─────────────────────────────────────────────────────────

describe("BrowserMockBridge (no Telegram SDK)", () => {
  beforeEach(() => {
    removeMockWebApp();
  });

  it("returns a bridge instance in non-Telegram environment", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(bridge).toBeDefined();
    expect(typeof bridge.ready).toBe("function");
    expect(typeof bridge.expand).toBe("function");
    expect(typeof bridge.getInitData).toBe("function");
    expect(bridge.requiresSessionHeaderFallback()).toBe(false);
    expect(typeof bridge.getColorScheme).toBe("function");
  });

  it("ready does not throw", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(() => bridge.ready()).not.toThrow();
  });

  it("expand does not throw", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(() => bridge.expand()).not.toThrow();
  });

  it("getInitData returns empty string", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(bridge.getInitData()).toBe("");
  });

  it("getColorScheme returns dark", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(bridge.getColorScheme()).toBe("dark");
  });

  it("haptic does not throw", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(() => bridge.haptic("light")).not.toThrow();
    expect(() => bridge.haptic("medium")).not.toThrow();
    expect(() => bridge.haptic("success")).not.toThrow();
    expect(() => bridge.haptic("error")).not.toThrow();
  });

  it("showBackButton does not throw", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(() => bridge.showBackButton()).not.toThrow();
  });

  it("hideBackButton does not throw", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(() => bridge.hideBackButton()).not.toThrow();
  });

  it("onBackButton returns unsubscribe function", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    const unsub = bridge.onBackButton(() => {});
    expect(typeof unsub).toBe("function");
    expect(() => unsub()).not.toThrow();
  });
});

describe("TelegramWebAppBridge (real Telegram SDK mock)", () => {
  let mock: MockWebApp;

  beforeEach(() => {
    mock = createMockWebApp();
    installMockWebApp(mock);
  });

  afterEach(() => {
    removeMockWebApp();
  });

  it("calls WebApp.ready()", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    bridge.ready();
    expect(mock.ready).toHaveBeenCalledOnce();
  });

  it("calls WebApp.expand()", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    bridge.expand();
    expect(mock.expand).toHaveBeenCalledOnce();
  });

  it("reads initData from WebApp.initData", async () => {
    mock.initData = "user=42&hash=secret";
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(bridge.getInitData()).toBe("user=42&hash=secret");
  });

  it("returns empty string when initData is empty", async () => {
    mock.initData = "";
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(bridge.getInitData()).toBe("");
  });

  it("requests the session header fallback only on Telegram Desktop", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    expect(createTelegramBridge().requiresSessionHeaderFallback()).toBe(true);
    mock.platform = "android";
    expect(createTelegramBridge().requiresSessionHeaderFallback()).toBe(false);
  });

  it("reads colorScheme from WebApp", async () => {
    mock.colorScheme = "light";
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(bridge.getColorScheme()).toBe("light");
  });

  it("calls BackButton.show()", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    bridge.showBackButton();
    expect(mock.BackButton.show).toHaveBeenCalledOnce();
  });

  it("calls BackButton.hide()", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    bridge.hideBackButton();
    expect(mock.BackButton.hide).toHaveBeenCalledOnce();
  });

  it("calls BackButton.onClick and offClick", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    const cb = vi.fn();
    bridge.onBackButton(cb);
    expect(mock.BackButton.onClick).toHaveBeenCalledWith(cb);

    // unsubscribe calls offClick
    const unsub = bridge.onBackButton(cb);
    unsub();
    expect(mock.BackButton.offClick).toHaveBeenCalledWith(cb);
  });

  it("calls HapticFeedback.impactOccurred for light/medium", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    bridge.haptic("light");
    expect(mock.HapticFeedback.impactOccurred).toHaveBeenCalledWith("light");
    bridge.haptic("medium");
    expect(mock.HapticFeedback.impactOccurred).toHaveBeenCalledWith("medium");
  });

  it("calls HapticFeedback.notificationOccurred for success/error", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    bridge.haptic("success");
    expect(mock.HapticFeedback.notificationOccurred).toHaveBeenCalledWith("success");
    bridge.haptic("error");
    expect(mock.HapticFeedback.notificationOccurred).toHaveBeenCalledWith("error");
  });

  it("calls showAlert", async () => {
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    await bridge.showAlert("hello");
    expect(mock.showAlert).toHaveBeenCalledWith("hello");
  });
});

describe("TelegramWebAppBridge graceful degradation", () => {
  afterEach(() => {
    removeMockWebApp();
  });

  it("getInitData returns '' when WebApp methods throw", async () => {
    const mock = createMockWebApp();
    installMockWebApp(mock);
    Object.defineProperty(mock, "initData", {
      get() {
        throw new Error("broken");
      },
    });
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(bridge.getInitData()).toBe("");
  });

  it("ready does not throw when WebApp throws", async () => {
    const mock = createMockWebApp();
    installMockWebApp(mock);
    mock.ready.mockImplementation(() => {
      throw new Error("broken");
    });
    const { createTelegramBridge } = await import(
      "../src/shared/telegram/factory"
    );
    const bridge = createTelegramBridge();
    expect(() => bridge.ready()).not.toThrow();
  });
});
