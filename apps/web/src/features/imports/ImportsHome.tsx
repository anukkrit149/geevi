"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Card, Empty, ErrorSummary, TextInput } from "@/components/ui";
import { ExportPanel } from "@/features/department/ExportPanel";
import { ApiError, api, newCommandId, unwrap } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useSession, useWorkspace } from "@/lib/session/session";
import { ArchiveRestore } from "./ArchiveRestore";
import { LegacyImportWizard } from "./LegacyImportWizard";
import { StagedJob } from "./StagedJob";

export function ImportsHome({ workspaceId }: { workspaceId: string }) {
  const { workspace, can } = useWorkspace(workspaceId);
  const { refresh } = useSession();
  const router = useRouter();
  const jobs = useWs(workspaceId, ["imports"], () => api.GET("/api/v1/workspaces/{workspace_id}/imports", { params: { path: { workspace_id: workspaceId } } }), can("archive.import") || can("legacy.import"));
  const [name, setName] = useState("");
  const [error, setError] = useState<ApiError | null>(null);

  if (!can("workspace.manage")) {
    return <div className="card" role="alert" data-testid="imports-denied"><h1>Import &amp; recovery</h1><p>Only the development operator can import, export or restore a workspace. This account has no such grant.</p></div>;
  }
  async function createWorkspace() {
    setError(null);
    try {
      const created = await unwrap(api.POST("/api/v1/workspaces", { body: { command_id: newCommandId(), name } }));
      await refresh();
      setName("");
      router.push(`/w/${created.id}/imports`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError("unexpected_failure", "The workspace was not created.", 0));
    }
  }
  const rows = [...(jobs.data ?? [])].reverse();

  return (
    <>
      <div className="page-head"><div><h1>Import &amp; recovery</h1><p>Workspace “{workspace?.name}”. The operator moves data; it holds no clinical read or approval authority.</p></div></div>
      <Card title="Staged and past imports" testId="jobs">
        {rows.length ? rows.map((job) => <StagedJob key={job.id} workspaceId={workspaceId} job={job} />) : <Empty>Nothing has been staged in this workspace.</Empty>}
      </Card>
      <div className="grid grid-2">
        <ArchiveRestore workspaceId={workspaceId} />
        <LegacyImportWizard workspaceId={workspaceId} />
      </div>
      <ExportPanel workspaceId={workspaceId} workspaceName={workspace?.name ?? "workspace"} />
      <Card title="Create an empty workspace" testId="create-workspace">
        <p className="small">Use a separate empty workspace to restore or import beside existing records.</p>
        <ErrorSummary error={error} onDismiss={() => setError(null)} />
        <form onSubmit={(e) => { e.preventDefault(); void createWorkspace(); }}>
          <TextInput label="Workspace name" value={name} onChange={setName} required />
          <Button type="submit">Create workspace</Button>
        </form>
      </Card>
    </>
  );
}
