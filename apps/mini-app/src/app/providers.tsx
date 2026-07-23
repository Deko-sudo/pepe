import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TelegramProvider } from "@/shared/telegram";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
});

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <TelegramProvider>{children}</TelegramProvider>
    </QueryClientProvider>
  );
}
