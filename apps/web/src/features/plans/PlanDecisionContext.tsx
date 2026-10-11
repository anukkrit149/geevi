"use client";

import Link from "next/link";
import { Badge } from "@/components/ui";
import { type Schemas } from "@/lib/api/client";
import { words } from "@/lib/format";

type Context = { protocol_title: string; protocol_version: number; protocol_scope: string; assessment: string | null; uncertainty: string | null;
  patient_goals: string | null; preferences: string | null; knowledge_cutoff_seq: number;
  criteria: { requirement_id: string; requirement_text: string; assessment: string; rationale: string }[];
  exceptions: { requirement_id: string; exception_type: string; departure: string; rationale: string; effective_status: string }[];
  unresolved: { text: string; next_action?: string }[];
  findings: { analyte: string; value_text: string | null; units: string | null; result_state: string; specimen_label: string | null; document_id: string }[] };

export function PlanDecisionContext({ workspaceId, view }: { workspaceId: string; view: Schemas["PlanView"] }) {
  const c = view.decision_context as unknown as Context;
  return <div data-testid="plan-decision-context">
    <h3>Patient and evidence considered for this version</h3>
    <p><Link href={`/w/${workspaceId}/department/protocols/${view.plan.protocol_version_id}`}>{c.protocol_title} · v{c.protocol_version}</Link></p><p className="small">{c.protocol_scope}</p>
    <p><strong>Assessment:</strong> {c.assessment || "No clinical assessment pinned."}</p>{c.uncertainty ? <p><strong>Uncertainty:</strong> {c.uncertainty}</p> : null}
    <p><strong>Patient goals:</strong> {c.patient_goals || "No patient discussion pinned."}</p>{c.preferences ? <p><strong>Preferences:</strong> {c.preferences}</p> : null}
    <p><strong>Individual rationale:</strong> {view.plan.rationale || "Not recorded"}</p><p><strong>Alternatives discussed:</strong> {view.plan.alternatives || "Not recorded"}</p>
    <h3>Applicability judgments</h3>{c.criteria.map((r) => <p className="small" key={r.requirement_id}>{r.requirement_text} <Badge value={r.assessment} />{r.rationale ? ` · ${r.rationale}` : ""}</p>)}
    <h3>Exceptions this plan relies on</h3>{c.exceptions.length ? c.exceptions.map((e) => <p key={e.requirement_id}>{e.requirement_id} · {e.exception_type} · <Badge value={e.effective_status} /><br />{e.departure}<br /><span className="small">Rationale: {e.rationale}</span></p>) : <p className="small">No exception is included in this plan.</p>}
    {c.unresolved.length ? <><h3>Unresolved at the pinned snapshot</h3>{c.unresolved.map((u, i) => <p className="small" key={i}>{u.text}{u.next_action ? ` · ${u.next_action}` : ""}</p>)}</> : null}
    <details><summary>Verified source findings in the pinned snapshot ({c.findings.length})</summary><p className="small">Captured at knowledge sequence {c.knowledge_cutoff_seq}. These are source findings, separate from the clinical assessment.</p>{c.findings.map((o, i) => <p className="small" key={i}>{o.analyte}: {o.value_text || words(o.result_state)}{o.units ? ` ${o.units}` : ""}{o.specimen_label ? ` · ${o.specimen_label}` : ""} · <Link href={`/w/${workspaceId}/patients/${view.plan.patient_id}/sources/${o.document_id}`}>Source document</Link></p>)}</details>
  </div>;
}
