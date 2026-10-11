"use client";

import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { api, setCsrfToken, unwrap, type Schemas } from "@/lib/api/client";

export type Session = Schemas["SessionOut"];
export type Workspace = Schemas["WorkspaceOut"];

/** Remove all cached server records (everything except the session entry itself). */
export function clearRecords(queryClient: QueryClient): void {
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== "session" });
}

type SessionState = {
  session: Session | null;
  loading: boolean;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
};

const SessionContext = createContext<SessionState>({ session: null, loading: true, signOut: async () => {}, refresh: async () => {} });

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      const result = await api.GET("/api/v1/session");
      if (result.response.status === 401) return null;
      return unwrap(Promise.resolve(result));
    },
    retry: false,
  });
  const session = query.data ?? null;
  useEffect(() => setCsrfToken(session?.csrf_token ?? null), [session]);

  const signOut = useCallback(async () => {
    setCsrfToken(session?.csrf_token ?? null);
    await api.DELETE("/api/v1/session").catch(() => undefined);
    setCsrfToken(null);
    // Drop every cached record and publish the signed-out state to all observers, so the next
    // account can never see the previous account's data.
    clearRecords(queryClient);
    queryClient.setQueryData(["session"], null);
  }, [queryClient, session]);
  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ["session"] });
  }, [queryClient]);

  const value = useMemo(() => ({ session, loading: query.isLoading, signOut, refresh }), [session, query.isLoading, signOut, refresh]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionState {
  return useContext(SessionContext);
}

/** Capabilities are for showing or hiding controls only. The server enforces every one of them again. */
export function useWorkspace(workspaceId: string): { workspace: Workspace | null; can: (capability: string) => boolean } {
  const { session } = useSession();
  const workspace = session?.workspaces.find((w) => w.id === workspaceId) ?? null;
  return { workspace, can: (capability) => !!workspace?.capabilities.includes(capability) };
}
