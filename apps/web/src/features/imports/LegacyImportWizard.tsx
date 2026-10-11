"use client";

import { useRef, useState } from "react";
import { Button, Card, ErrorSummary } from "@/components/ui";
import { ApiError, api, fileToBase64 } from "@/lib/api/client";
import { useAction } from "@/lib/api/useAction";

/**
 * Explicit legacy import. This origin cannot read the old prototype's localStorage or IndexedDB, so the
 * user supplies captured store JSON (or exported case packets) and the exact original files.
 */
export function LegacyImportWizard({ workspaceId }: { workspaceId: string }) {
  const action = useAction(workspaceId);
  const snapshotRef = useRef<HTMLInputElement>(null);
  const originalsRef = useRef<HTMLInputElement>(null);
  const [local, setLocal] = useState<ApiError | null>(null);
  const [summary, setSummary] = useState<string | null>(null);

  async function stage() {
    setLocal(null);
    setSummary(null);
    const snapshots: Record<string, unknown> = {};
    const packets: Record<string, unknown>[] = [];
    try {
      for (const file of Array.from(snapshotRef.current?.files ?? [])) {
        const parsed = JSON.parse(await file.text());
        if (parsed && parsed.prototype && parsed.case) packets.push(parsed);
        else if (parsed && typeof parsed === "object" && !Array.isArray(parsed) && Object.keys(parsed).some((k) => k.startsWith("casebook-"))) Object.assign(snapshots, parsed);
        else snapshots[file.name.replace(/\.json$/i, "")] = parsed;
      }
    } catch {
      setLocal(new ApiError("invalid_json", "A selected snapshot file is not valid JSON.", 422, "Capture the legacy store again and select the JSON file."));
      return;
    }
    const originals = await Promise.all(Array.from(originalsRef.current?.files ?? []).map(async (file) => ({ filename: file.name, media_type: file.type || "application/pdf", content_base64: await fileToBase64(file) })));
    const job = await action.run("legacy", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/imports/legacy", {
      params: { path: { workspace_id: workspaceId } }, body: { command_id, snapshots, packets, originals } }), "Legacy data staged for review (nothing is active yet)");
    if (job) setSummary(`Staged: ${String((job.report as Record<string, any>).documents)} document(s), ${String((job.report as Record<string, any>).originals_supplied)} original(s) matched by hash.`);
  }

  return (
    <Card title="Import from the legacy prototype" testId="legacy-import">
      <ol className="small">
        <li>In the old prototype&apos;s browser tab, capture the <span className="mono">casebook-intake-v1</span> (and optionally <span className="mono">casebook-research-lab-v1</span>) localStorage values to a JSON file, or use its “export case” packet.</li>
        <li>Select the exact original report files. They are matched by SHA-256, never by filename.</li>
        <li>Review the staged report, then explicitly activate. Legacy approvals stay unmapped history.</li>
      </ol>
      <p className="small">The older standalone <span className="mono">casebook-evidence-demo-v2</span> format is excluded. Nothing in the legacy app or its browser storage is read or changed.</p>
      <ErrorSummary error={local ?? action.error} onDismiss={() => { setLocal(null); action.clearError(); }} />
      <form onSubmit={(e) => { e.preventDefault(); void stage(); }}>
        <div className="grid grid-2">
          <div className="field"><label htmlFor="legacy-snapshots">Captured snapshot or packet JSON</label><input id="legacy-snapshots" ref={snapshotRef} type="file" accept="application/json,.json" multiple required /></div>
          <div className="field"><label htmlFor="legacy-originals">Exact original files (PDF/PNG/JPEG)</label><input id="legacy-originals" ref={originalsRef} type="file" accept="application/pdf,image/png,image/jpeg" multiple /></div>
        </div>
        <Button variant="primary" type="submit" busy={action.pending === "legacy"}>Stage legacy import</Button>
      </form>
      {summary ? <p role="status" data-testid="legacy-staged">{summary}</p> : null}
    </Card>
  );
}
