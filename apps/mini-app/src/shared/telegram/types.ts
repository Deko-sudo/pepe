export interface TelegramBridge {
  ready(): void;
  expand(): void;
  getInitData(): string;
  getColorScheme(): "light" | "dark";
  showBackButton(): void;
  hideBackButton(): void;
  haptic(type: "light" | "medium" | "success" | "error"): void;
  showAlert(message: string): Promise<void>;
  onBackButton(callback: () => void): () => void;
}
