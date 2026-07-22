import type { TelegramBridge } from "./types";

declare global {
  interface Window {
    TelegramWebApp?: unknown;
    __INIT_DATA__?: unknown;
  }
}

function isTelegramWebView(): boolean {
  try {
    return (
      typeof window !== "undefined" &&
      Boolean(window.TelegramWebApp || window.__INIT_DATA__)
    );
  } catch {
    return false;
  }
}

class TelegramWebAppBridge implements TelegramBridge {
  ready(): void {
    try {
      (window as unknown as Record<string, { ready: () => void }>).TelegramWebApp?.ready?.();
    } catch {
      // Silent fail
    }
  }

  expand(): void {
    try {
      (window as unknown as Record<string, { expand: () => void }>).TelegramWebApp?.expand?.();
    } catch {
      // Silent fail
    }
  }

  getInitData(): string {
    try {
      return typeof window.__INIT_DATA__ === "string" ? window.__INIT_DATA__ : "";
    } catch {
      return "";
    }
  }

  getColorScheme(): "light" | "dark" {
    try {
      const app = window.TelegramWebApp as Record<string, unknown> | undefined;
      const themeParams = app?.themeParams as Record<string, string> | undefined;
      const bg = themeParams?.bg_color;
      if (bg) {
        const hex = bg.replace("#", "");
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance > 0.5 ? "light" : "dark";
      }
    } catch {
      // Fall through
    }
    return "dark";
  }

  showBackButton(): void {
    try {
      (window as unknown as Record<string, { showBackButton: () => void }>).TelegramWebApp?.showBackButton?.();
    } catch {
      // Silent fail
    }
  }

  hideBackButton(): void {
    try {
      (window as unknown as Record<string, { hideBackButton: () => void }>).TelegramWebApp?.hideBackButton?.();
    } catch {
      // Silent fail
    }
  }

  haptic(_type: "light" | "medium" | "success" | "error"): void {
    try {
      const app = window.TelegramWebApp as Record<string, unknown> | undefined;
      const haptic = app?.HapticFeedback as Record<string, (s: string) => void> | undefined;
      haptic?.impactOccurred?.(_type);
    } catch {
      // Silent fail
    }
  }

  async showAlert(message: string): Promise<void> {
    try {
      (window as unknown as Record<string, { showAlert: (m: string) => void }>).TelegramWebApp?.showAlert?.(message);
    } catch {
      window.alert(message);
    }
  }

  onBackButton(callback: () => void): () => void {
    try {
      (window as unknown as Record<string, { onBackButton: (cb: () => void) => void }>).TelegramWebApp?.onBackButton?.(callback);
    } catch {
      // Silent fail
    }
    return () => {};
  }
}

class BrowserMockBridge implements TelegramBridge {
  ready(): void {}
  expand(): void {}
  getInitData(): string {
    return "";
  }
  getColorScheme(): "light" | "dark" {
    return "dark";
  }
  showBackButton(): void {}
  hideBackButton(): void {}
  haptic(_type: "light" | "medium" | "success" | "error"): void {}
  async showAlert(message: string): Promise<void> {
    window.alert(message);
  }
  onBackButton(_callback: () => void): () => void {
    return () => {};
  }
}

export function createTelegramBridge(): TelegramBridge {
  if (isTelegramWebView()) {
    return new TelegramWebAppBridge();
  }
  return new BrowserMockBridge();
}
