"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Select, TextArea } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { when, words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

type Review = Schemas["ApplicabilityReviewOut"];
type Protocol = Schemas["ProtocolVersionOut"];
type Criterion = { requirement_id: string; assessment: string | null; rationale: string; supporting: { kind: string; id: string }[] };
const CHOICES = ["match", "difference", "unknown", "not_applicable"];

function CriteriaEditor({ workspaceId, review, protocol }: { workspaceId: string; review: Review; protocol: Protocol }) {
  const action = useAction(workspaceId);
  const [criteria, setCriteria] = useState<Criterion[]>(review.criteria as Criterion[]);
  const [base, setBase] = useState(review.revision);
  const update = (id: string, patch: Partial<Criterion>) => setCriteria((cs) => cs.map((c) => (c.requirement_id === id ? { ...c, ...patch } : c)));
  const body = (command_id: string, expected_revision: number) => ({ command_id, expected_revision, criteria: criteria as never });

  async function save(): Promise<number | null> {
    const done = await action.run("save", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/applicability/{review_id}/save", {
      params: { path: { workspace_id: workspaceId, review_id: review.id } }, body: body(command_id, base) }), "Applicability draft saved");
    if (!done?.target) return null;
    setBase(done.target.revision);
    return done.target.revision;
  }
  async function accept() {
    const revision = await save();
    if (revision === null) return;
    await action.run("accept", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/applicability/{review_id}/accept", {
      params: { path: { workspace_id: workspaceId, review_id: review.id } }, body: { command_id, expected_revision: revision } }), "Applicability review accepted");
  }

  return (
    <div data-testid="applicability-editor">
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {(protocol.requirements as Record<string, any>[]).map((r) => {
        const c = criteria.find((x) => x.requirement_id === r.id) ?? { requirement_id: r.id, assessment: null, rationale: "", supporting: [] };
        return (
          <fieldset key={r.id} data-testid={`criterion-${r.id}`}>
            <legend>{r.id} <span className="small">· {words(r.kind)} · gate: {r.gate} · {r.waiver?.allowed ? `${r.waiver.exception_type} exception permitted` : "non-waivable"}</span></legend>
            <p>{r.text}</p>
            {r.branch ? <p className="small">Authored branch — default: {r.branch.default}; alternate: {r.branch.alternate}</p> : null}
            <div className="row" role="radiogroup" aria-label={`Assessment for ${r.id}`}>
              {CHOICES.map((choice) => (
                <label key={choice} className="check" style={{ marginBottom: 0 }}>
                  <input type="radio" name={`a-${review.id}-${r.id}`} checked={c.assessment === choice} onChange={() => update(r.id, { assessment: choice })} />
                  {words(choice)}
                </label>
              ))}
            </div>
            <TextArea label={`Rationale for ${r.id}`} rows={2} value={c.rationale} onChange={(rationale) => update(r.id, { rationale })}
              hint="Required for ‘difference’ and ‘not applicable’. Unknown stays unknown: an exception never converts it." />
          </fieldset>
        );
      })}
      <div className="row">
        <Button busy={action.pending === "save"} onClick={() => void save()}>Save draft</Button>
        <Button variant="primary" busy={action.pending === "accept"} onClick={() => void accept()}>Accept applicability review</Button>
      </div>
    </div>
  );
}

export function ApplicabilityReview({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const reviews = useWs(workspaceId, ["patient", patientId, "applicability"], () =>
    api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/applicability", { params: { path: { workspace_id: workspaceId, patient_id: patientId } } }));
  const protocols = useWs(workspaceId, ["protocols"], () => api.GET("/api/v1/workspaces/{workspace_id}/protocols", { params: { path: { workspace_id: workspaceId } } }));
  const action = useAction(workspaceId);
  const selectable = (protocols.data ?? []).filter((p) => p.selectable);
  const [choice, setChoice] = useState("");
  const protocolId = choice || selectable[0]?.id || "";
  const byId = new Map((protocols.data ?? []).map((p) => [p.id, p]));
  const rows = [...(reviews.data ?? [])].reverse();

  return (
    <Card title="Applicability of the shared protocol" testId="applicability">
      <p className="small">Criterion-level review against one exact published protocol version. Each assessment is the treating clinician&apos;s attributed judgement.</p>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {can("clinical.assess") ? (
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div style={{ minWidth: 340 }}>
            <Select label="Effective protocol version" value={protocolId} onChange={setChoice}
              options={selectable.length ? selectable.map((p) => ({ value: p.id, label: `${p.title} — v${p.version_no}` })) : [{ value: "", label: "No effective protocol version" }]} />
          </div>
          <Button disabled={!protocolId} busy={action.pending === "start"} onClick={() => action.run("start", (command_id) =>
            api.POST("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/applicability", { params: { path: { workspace_id: workspaceId, patient_id: patientId } },
              body: { command_id, protocol_version_id: protocolId } }), "Applicability draft started")} style={{ marginBottom: ".6rem" }}>
            Start applicability review
          </Button>
        </div>
      ) : null}
      {rows.length ? rows.map((review) => {
        const protocol = byId.get(review.protocol_version_id);
        return (
          <div className="item" key={review.id} data-testid={`applicability-${review.status}`}>
            <div className="row">
              <strong>Review v{review.version_no}</strong><Badge value={review.status} />
              {protocol ? <Link href={`/w/${workspaceId}/department/protocols/${protocol.id}`}>{protocol.title} v{protocol.version_no}</Link> : null}
              <span className="small">{review.recorded_by_name}{review.accepted_at ? ` · accepted ${when(review.accepted_at)}` : ""}</span>
            </div>
            {review.status === "draft" && protocol && can("clinical.assess") ? <CriteriaEditor workspaceId={workspaceId} review={review} protocol={protocol} /> : (
              <ul>{(review.criteria as Criterion[]).map((c) => (
                <li key={c.requirement_id}>{c.requirement_id}: <Badge value={c.assessment ?? "pending"} />{c.rationale ? <span className="small"> — {c.rationale}</span> : null}</li>
              ))}</ul>
            )}
          </div>
        );
      }) : <Empty>No applicability review yet.</Empty>}
    </Card>
  );
}
