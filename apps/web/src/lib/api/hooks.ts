"use client";

import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "./client";

type Call<T> = () => Promise<{ data?: T; error?: unknown; response: Response }>;

/** Workspace-scoped server state. Keys always start with the workspace id so records never cross workspaces. */
export function useWs<T>(workspaceId: string, key: readonly unknown[], call: Call<T>, enabled = true) {
  return useQuery({ queryKey: ["ws", workspaceId, ...key], queryFn: () => unwrap(call()), enabled });
}

export function useMembers(workspaceId: string) {
  return useWs(workspaceId, ["members"], () => api.GET("/api/v1/workspaces/{workspace_id}/members", { params: { path: { workspace_id: workspaceId } } }));
}

export function usePatient(workspaceId: string, patientId: string) {
  return useWs(workspaceId, ["patient", patientId, "detail"], () =>
    api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}", { params: { path: { workspace_id: workspaceId, patient_id: patientId } } }));
}

/** Development-only scenario text used to prefill demo forms; absent outside development mode. */
export function useScenario() {
  return useQuery({
    queryKey: ["dev-scenario"],
    queryFn: async () => ((await api.GET("/api/v1/dev/scenario")).data ?? null) as Record<string, any> | null,
    staleTime: Infinity,
  });
}
