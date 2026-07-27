import { Outlet } from "react-router-dom";
import { AuthBanner } from "@/features/auth/auth-banner";
import { BottomNav } from "@/features/navigation/bottom-nav";

export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <AuthBanner />
      <main className="flex-1 pb-16"><Outlet /></main>
      <BottomNav />
    </div>
  );
}
