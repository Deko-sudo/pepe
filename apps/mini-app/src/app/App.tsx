import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import { Providers } from "./providers";
import { BottomNav } from "@/features/navigation/bottom-nav";

export function App() {
  return (
    <Providers>
      <div className="flex min-h-screen flex-col">
        <main className="flex-1 pb-16">
          <RouterProvider router={router} />
        </main>
        <BottomNav />
      </div>
    </Providers>
  );
}
