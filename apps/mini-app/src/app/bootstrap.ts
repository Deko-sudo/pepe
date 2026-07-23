import { createTelegramBridge } from "@/shared/telegram";

export function bootstrap(): void {
  const bridge = createTelegramBridge();

  bridge.expand();
  bridge.ready();
}
