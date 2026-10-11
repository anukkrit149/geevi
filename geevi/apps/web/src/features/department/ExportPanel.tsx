"use client";

import { useState } from "react";
import { Badge, Button, Card, ErrorSummary, Meta } from "@/components/ui";
import { ApiError, api, unwrap, type Schemas } from "@/lib/api/client";
import { when } from "@/lib/format";

type Archive = Schemas["Archive"];

function download(name: string, archive: Archive) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(archive)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

/** Full backup (records + original bytes) or an explicitly incomplete review-only packet. */
export function ExportPanel({ workspaceId, workspaceName }: { workspaceId: string; workspaceName: string }) {
  const [archive, setArchive] = useState<Archive | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  async function run(mode: "full" | "review") {
    setBusy(mode);
    setError(null);
    try {
      const result = await unwrap(api.GET("/api/v1/workspaces/{workspace_id}/archive", { params: { path: { workspace_id: workspaceId }, query: { mode } } }));
      setArchive(result);
      download(`geevi-${mode === "full" ? "backup" : "review-packet"}-${workspaceName.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.json`, result);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError("unexpected_failure", "Export failed.", 0));
    } finally {
      setBusy(null);
    }
  }
  return (
    <Card title="Export this workspace" testId="export">
      <p className="small">A full backup contains every record, history, receipt and the original bytes. It never contains passwords, sessions or grants. A review-only packet omits the bytes and is not a backup.</p>
      <ErrorSummary error={error} onDismiss={() => setError(null)} />
      <div className="row">
        <Button variant="primary" busy={busy === "full"} onClick={() => void run("full")}>Download full backup</Button>
        <Button busy={busy === "review"} onClick={() => void run("review")}>Download review-only packet</Button>
      </div>
      {archive ? (
        <div data-testid="export-result">
          <div className="row" style={{ marginTop: ".6rem" }}>
            <Badge value={archive.complete ? "approved" : "failed"} label={archive.complete ? "Complete backup" : "INCOMPLETE — not a full backup"} />
            <span className="small">{archive.kind.replace("_", " ")} · taken {when(String(archive.snapshot.taken_at))} at sequence {String(archive.snapshot.sequence)}</span>
          </div>
          {archive.incomplete_reasons.length ? <ul data-testid="incomplete-reasons">{archive.incomplete_reasons.map((r) => <li key={r}>{r}</li>)}</ul> : null}
          <Meta items={[["Originals", `${archive.originals.filter((o) => o.available).length} of ${archive.originals.length} with intact bytes`],
            ["Records", Object.values(archive.counts).reduce((a, b) => a + b, 0)], ["Content digest", <span className="mono" key="d">{archive.content_digest}</span>],
            ["Excluded by design", archive.excluded.join(", ")]]} />
        </div>
      ) : null}
    </Card>
  );
}
