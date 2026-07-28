import type { TelegramBridge } from "./types";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready(): void;
        expand(): void;
        initData: string;
        platform?: string;
        colorScheme: "light" | "dark";
        themeParams: {
          bg_color?: string;
          text_color?: string;
          hint_color?: string;
          link_color?: string;
          button_color?: string;
          button_text_color?: string;
        };
        BackButton: {
          show(): void;
          hide(): void;
          onClick(callback: () => void): void;
          offClick(callback: () => void): void;
        };
        HapticFeedback: {
          impactOccurred(type: "light" | "medium"): void;
          notificationOccurred(type: "success" | "error"): void;
        };
        showAlert(message: string, callback?: () => void): void;
      };
    };
  }
}

function isTelegramWebView(): boolean {
  try {
    return (
      typeof window !== "undefined" &&
      Boolean(window.Telegram?.WebApp)
    );
  } catch {
    return false;
  }
}

function getWebApp(): NonNullable<NonNullable<Window["Telegram"]>["WebApp"]> {
  return window.Telegram!.WebApp!;
}

class TelegramWebAppBridge implements TelegramBridge {
  ready(): void {
    try {
      getWebApp().ready();
    } catch {
      // Silent fail
    }
  }

  expand(): void {
    try {
      getWebApp().expand();
    } catch {
      // Silent fail
    }
  }

  getInitData(): string {
    try {
      return getWebApp().initData ?? "";
    } catch {
      return "";
    }
  }

  requiresSessionHeaderFallback(): boolean {
    try {
      return getWebApp().platform === "tdesktop";
    } catch {
      return false;
    }
  }

  getColorScheme(): "light" | "dark" {
    try {
      return getWebApp().colorScheme;
    } catch {
      return "dark";
    }
  }

  showBackButton(): void {
    try {
      getWebApp().BackButton.show();
    } catch {
      // Silent fail
    }
  }

  hideBackButton(): void {
    try {
      getWebApp().BackButton.hide();
    } catch {
      // Silent fail
    }
  }

  haptic(type: "light" | "medium" | "success" | "error"): void {
    try {
      if (type === "light" || type === "medium") {
        getWebApp().HapticFeedback.impactOccurred(type);
      } else {
        getWebApp().HapticFeedback.notificationOccurred(type);
      }
    } catch {
      // Silent fail
    }
  }

  async showAlert(message: string): Promise<void> {
    try {
      getWebApp().showAlert(message);
    } catch {
      window.alert(message);
    }
  }

  onBackButton(callback: () => void): () => void {
    try {
      getWebApp().BackButton.onClick(callback);
    } catch {
      // Silent fail
    }
    return () => {
      try {
        getWebApp().BackButton.offClick(callback);
      } catch {
        // Silent fail
      }
    };
  }
}

class BrowserMockBridge implements TelegramBridge {
  ready(): void {}
  expand(): void {}
  getInitData(): string {
    return "";
  }
  requiresSessionHeaderFallback(): boolean {
    return false;
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
