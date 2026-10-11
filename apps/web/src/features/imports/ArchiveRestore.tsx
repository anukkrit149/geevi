"use client";

import { useRef, useState } from "react";
import { Button, Card, ErrorSummary } from "@/components/ui";
import { ApiError, api } from "@/lib/api/client";
import { useAction } from "@/lib/api/useAction";

/** Restore an archive into a separate staging container; activation is a distinct operator decision. */
export function ArchiveRestore({ workspaceId }: { workspaceId: string }) {
  const action = useAction(workspaceId);
  const fileRef = useRef<HTMLInputElement>(null);
  const [local, setLocal] = useState<ApiError | null>(null);

  async function stage() {
    setLocal(null);
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    let archive: Record<string, unknown>;
    try {
      archive = JSON.parse(await file.text());
    } catch {
      setLocal(new ApiError("invalid_json", "The selected file is not a valid archive (JSON).", 422, "Select a Geevi archive file."));
      return;
    }
    const job = await action.run(`archive:${file.name}:${file.size}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/imports/archive", {
      params: { path: { workspace_id: workspaceId } }, body: { command_id, archive } }), "Archive validated into staging (nothing is active yet)");
    if (job && fileRef.current) fileRef.current.value = "";
  }

  return (
    <Card title="Restore from an archive" testId="archive-restore">
      <p className="small">The archive is checked for schema, sizes, hashes and references inside a staging container. Accounts, sessions and grants are never imported, and nothing active is rewritten.</p>
      <ErrorSummary error={local ?? action.error} onDismiss={() => { setLocal(null); action.clearError(); }} />
      <form onSubmit={(e) => { e.preventDefault(); void stage(); }}>
        <div className="field"><label htmlFor="archive-file">Archive file</label><input id="archive-file" ref={fileRef} type="file" accept="application/json,.json" required /></div>
        <Button variant="primary" type="submit" busy={!!action.pending}>Validate into staging</Button>
      </form>
    </Card>
  );
}
