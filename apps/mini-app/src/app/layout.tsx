import { Outlet } from "react-router-dom";
import { AuthBanner } from "@/features/auth/auth-banner";
import { BottomNav } from "@/features/navigation/bottom-nav";

export function AppLayout() {
  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden">
      <AuthBanner />
      <main className="min-h-0 flex-1 overflow-y-auto pb-24"><Outlet /></main>
      <BottomNav />
    </div>
  );
}
