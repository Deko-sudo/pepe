import type { TelegramValidationState, TelegramUser } from "@/shared/api";
import type { DiagnosticCode } from "@/shared/diagnostics";

export interface TelegramBridge {
  ready(): void;
  expand(): void;
  getInitData(): string;
  requiresSessionHeaderFallback(): boolean;
  getColorScheme(): "light" | "dark";
  showBackButton(): void;
  hideBackButton(): void;
  haptic(type: "light" | "medium" | "success" | "error"): void;
  showAlert(message: string): Promise<void>;
  onBackButton(callback: () => void): () => void;
}

export type TelegramInitState = "TG_INIT_WAITING" | "TG_INIT_TIMEOUT" | "TG_READY";

export interface TelegramAuthState {
  state: TelegramValidationState;
  telegramInitState: TelegramInitState;
  user: TelegramUser | null;
  error: string | null;
  diagnosticCode: DiagnosticCode | null;
  logout(): Promise<void>;
  logoutAll(): Promise<void>;
}
