import { useTelegramAuth } from "@/shared/telegram";

export function AuthBanner() {
  const { state, error } = useTelegramAuth();

  if (state !== "invalid" && state !== "unavailable") {
    return null;
  }

  return (
    <div className="mx-4 mt-4 rounded-xl border border-negative/30 bg-negative/10 px-4 py-3">
      <p className="text-sm text-negative">{error}</p>
    </div>
  );
}
