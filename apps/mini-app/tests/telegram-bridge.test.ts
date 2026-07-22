import { describe, it, expect } from "vitest";
import { createTelegramBridge } from "../src/shared/telegram/factory";

describe("TelegramBridge factory", () => {
  it("returns a bridge instance in non-Telegram environment", () => {
    const bridge = createTelegramBridge();
    expect(bridge).toBeDefined();
    expect(typeof bridge.ready).toBe("function");
    expect(typeof bridge.expand).toBe("function");
    expect(typeof bridge.getInitData).toBe("function");
    expect(typeof bridge.getColorScheme).toBe("function");
  });
});

describe("Browser Mock Bridge", () => {
  const bridge = createTelegramBridge();

  it("ready does not throw", () => {
    expect(() => bridge.ready()).not.toThrow();
  });

  it("expand does not throw", () => {
    expect(() => bridge.expand()).not.toThrow();
  });

  it("getInitData returns empty string in browser", () => {
    expect(bridge.getInitData()).toBe("");
  });

  it("getColorScheme returns dark", () => {
    expect(bridge.getColorScheme()).toBe("dark");
  });

  it("haptic does not throw", () => {
    expect(() => bridge.haptic("light")).not.toThrow();
    expect(() => bridge.haptic("medium")).not.toThrow();
    expect(() => bridge.haptic("success")).not.toThrow();
    expect(() => bridge.haptic("error")).not.toThrow();
  });

  it("showBackButton does not throw", () => {
    expect(() => bridge.showBackButton()).not.toThrow();
  });

  it("hideBackButton does not throw", () => {
    expect(() => bridge.hideBackButton()).not.toThrow();
  });

  it("onBackButton returns unsubscribe function", () => {
    const unsub = bridge.onBackButton(() => {});
    expect(typeof unsub).toBe("function");
    expect(() => unsub()).not.toThrow();
  });
});
