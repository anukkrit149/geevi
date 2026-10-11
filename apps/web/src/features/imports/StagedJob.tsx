"use client";

import { Badge, Button, ErrorSummary, Meta } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useAction } from "@/lib/api/useAction";
import { when } from "@/lib/format";

export type Job = Schemas["ImportJobOut"];

/** A staged import: validation report, honest disclosures, and the separate explicit activation. */
export function StagedJob({ workspaceId, job }: { workspaceId: string; job: Job }) {
  const action = useAction(workspaceId);
  const report = job.report as Record<string, any>;
  const params = { path: { workspace_id: workspaceId, job_id: job.id } };
  return (
    <div className="item" data-testid={`job-${job.kind}`} data-status={job.status}>
      <div className="row">
        <strong>{job.kind === "legacy" ? "Legacy conversion" : "Archive restore"}</strong>
        <span data-testid="job-status"><Badge value={job.status} /></span>
        {report.complete === true ? <Badge value="approved" label="complete" /> : <span data-testid="job-incomplete"><Badge value="failed" label="INCOMPLETE" /></span>}
        <span className="small">staged by {job.created_by_name} · {when(job.created_at)}</span>
      </div>
      <Meta items={[["Source fingerprint", <span className="mono" key="f">{job.source_fingerprint.slice(0, 24)}…</span>],
        ["Patients", report.patients], ["Documents", report.documents], ["Originals supplied", report.originals_supplied],
        ["Candidate findings", report.candidates], ["Records", report.counts ? Object.values(report.counts as Record<string, number>).reduce((a, b) => a + b, 0) : null]]} />
      {report.missing_originals?.length ? (
        <div data-testid="missing-originals"><strong>Missing originals (unavailable until the exact file is supplied):</strong>
          <ul>{(report.missing_originals as Record<string, string>[]).map((m) => <li key={m.sha256}>{m.patient}: {m.document} <span className="mono">({m.sha256.slice(0, 12)}…)</span></li>)}</ul></div>
      ) : null}
      {report.incomplete_reasons?.length ? <ul data-testid="incomplete-reasons">{(report.incomplete_reasons as string[]).map((r) => <li key={r}>{r}</li>)}</ul> : null}
      {report.unmapped && Object.keys(report.unmapped).length ? (
        <p data-testid="unmapped">Preserved as unmapped legacy history (never a signature or publication here): {Object.entries(report.unmapped as Record<string, number>).map(([k, n]) => `${n} ${k}`).join(", ")}</p>
      ) : null}
      {report.disclosures?.length ? <ul data-testid="disclosures">{(report.disclosures as string[]).map((d) => <li className="small" key={d}>{d}</li>)}</ul> : null}
      {report.errors?.length ? <p className="small">Validation failed: {String(report.errors[0].message)}</p> : null}
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {job.status === "validated" ? (
        <div className="row">
          <Button variant="primary" busy={action.pending === `activate:${job.id}`} onClick={() => action.run(`activate:${job.id}`, (command_id) =>
            api.POST("/api/v1/workspaces/{workspace_id}/imports/{job_id}/activate", { params, body: { command_id } }), "Activated: this workspace now uses the imported records")}>
            Activate in this workspace
          </Button>
          <Button onClick={() => action.run(`discard:${job.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/imports/{job_id}/discard", { params, body: { command_id } }), "Staged import discarded")}>Discard</Button>
          <span className="small">Until you activate, the current workspace is untouched.</span>
        </div>
      ) : null}
    </div>
  );
}
