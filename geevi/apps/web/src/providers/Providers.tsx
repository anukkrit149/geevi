"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { StatusProvider } from "@/components/status";
import { SessionProvider } from "@/lib/session/session";

export function Providers({ children }: { children: ReactNode }) {
  // Server state lives in memory only (no persistence), is refetched on focus, and is cleared on sign-out.
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 0, gcTime: 5 * 60_000, refetchOnWindowFocus: true, retry: false }, mutations: { retry: false } },
  }));
  return (
    <QueryClientProvider client={client}>
      <StatusProvider>
        <SessionProvider>{children}</SessionProvider>
      </StatusProvider>
    </QueryClientProvider>
  );
}
