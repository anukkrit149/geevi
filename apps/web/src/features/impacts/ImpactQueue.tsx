"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Loading, Select, TextInput } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { when, words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

type Impact = Schemas["ImpactReviewOut"];
type Form = { disposition: string; rationale: string; review_trigger: string; linked: string };
const BLANK: Form = { disposition: "retained", rationale: "", review_trigger: "", linked: "" };

function ImpactItem({ workspaceId, impact, patientName }: { workspaceId: string; impact: Impact; patientName: string }) {
  const { can } = useWorkspace(workspaceId);
  const action = useAction(workspaceId);
  const plans = useWs(workspaceId, ["patient", impact.patient_id, "plans"], () =>
    api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/plans", { params: { path: { workspace_id: workspaceId, patient_id: impact.patient_id } } }), impact.state !== "closed");
  const [form, setForm] = useState<Form>(BLANK);
  const params = { path: { workspace_id: workspaceId, impact_id: impact.id } };
  const successors = (plans.data ?? []).filter((v) => v.plan.status === "approved" && v.plan.version_no > impact.plan_version_no);
  const open = impact.state !== "closed";

  return (
    <div className="item" data-testid={`impact-${patientName.split(" ")[0].toLowerCase()}`} data-state={impact.state}>
      <div className="row">
        <Link className="item-title" href={`/w/${workspaceId}/patients/${impact.patient_id}/decisions`}>{patientName}</Link>
        <span data-testid="impact-state"><Badge value={impact.state} /></span>
        {impact.disposition ? <Badge value={impact.disposition === "adopted" ? "approved" : "reviewed"} label={words(impact.disposition)} /> : null}
        {impact.needs_classification ? <Badge value="pending" label="needs classification" /> : null}
      </div>
      <p>{impact.change.description}</p>
      <p className="small">Affects plan v{impact.plan_version_no} · scope {impact.scope_key.split("/").slice(2).join("/") || impact.scope_key} · owner {impact.owner_name} · opened {when(impact.recorded_at)}</p>
      {impact.rationale ? <p className="quote">{impact.rationale}{impact.review_trigger ? ` · review trigger: ${impact.review_trigger}` : ""}</p> : null}
      {impact.next_action ? <p className="small"><strong>Next:</strong> {impact.next_action}</p> : null}
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {open && can("impact.resolve") ? (
        impact.needs_classification ? (
          <fieldset>
            <legend>Classify this incoming material</legend>
            <TextInput label="Rationale" value={form.rationale} onChange={(rationale) => setForm({ ...form, rationale })} />
            <div className="row">
              {[true, false].map((relevant) => (
                <Button key={String(relevant)} onClick={() => action.run(`classify:${impact.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/impacts/{impact_id}/classify", {
                  params, body: { command_id, expected_revision: impact.revision, relevant, rationale: form.rationale } }), relevant ? "Classified as relevant; disposition still required" : "Classified as not relevant; closed")}>
                  {relevant ? "Relevant to this plan" : "Not relevant (close)"}
                </Button>
              ))}
            </div>
          </fieldset>
        ) : (
          <fieldset>
            <legend>Record a disposition for {patientName}</legend>
            <div className="grid grid-2">
              <Select label="Disposition" value={form.disposition} onChange={(disposition) => setForm({ ...form, disposition })}
                options={[{ value: "retained", label: "Retain the current plan (with review trigger)" }, { value: "adopted", label: "Adopted through a newly approved plan" },
                  { value: "more_information", label: "More information needed (stays open)" }, { value: "not_applicable", label: "Not applicable to this patient" }, { value: "unaffected", label: "Plan unaffected" }]} />
              {form.disposition === "retained" ? <TextInput label="Review trigger" value={form.review_trigger} onChange={(review_trigger) => setForm({ ...form, review_trigger })} /> : null}
              {form.disposition === "adopted" ? (
                <Select label="Newly approved successor plan" value={form.linked} onChange={(linked) => setForm({ ...form, linked })}
                  options={[{ value: "", label: successors.length ? "Select the successor plan…" : "No approved successor plan exists yet" }, ...successors.map((v) => ({ value: v.plan.id, label: `Plan v${v.plan.version_no} (approved)` }))]} />
              ) : null}
            </div>
            <TextInput label="Rationale" value={form.rationale} onChange={(rationale) => setForm({ ...form, rationale })} />
            <Button variant="primary" busy={action.pending === `resolve:${impact.id}`} onClick={async () => {
              const done = await action.run(`resolve:${impact.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/impacts/{impact_id}/resolve", {
                params, body: { command_id, expected_revision: impact.revision, disposition: form.disposition as never, rationale: form.rationale,
                  review_trigger: form.review_trigger || null, linked_plan_version_id: form.linked || null } }), "Impact disposition recorded");
              if (done) setForm(BLANK);
            }}>Record disposition</Button>
          </fieldset>
        )
      ) : null}
      <details><summary className="small">History ({impact.history.length})</summary>
        <ul>{(impact.history as Record<string, any>[]).map((h, i) => <li className="small" key={i}>{words(String(h.event))}{h.by ? ` — ${h.by}` : ""}{h.rationale ? ` — ${h.rationale}` : h.reason ? ` — ${h.reason}` : ""}</li>)}</ul>
      </details>
    </div>
  );
}

/** Each change creates a separate, owned impact review per patient plan. Resolving one never resolves another. */
export function ImpactQueue({ workspaceId }: { workspaceId: string }) {
  const ws = { workspace_id: workspaceId };
  const impacts = useWs(workspaceId, ["impacts"], () => api.GET("/api/v1/workspaces/{workspace_id}/impacts", { params: { path: ws } }));
  const patients = useWs(workspaceId, ["patients"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients", { params: { path: ws } }));
  const names = new Map((patients.data ?? []).map((p) => [p.patient.id, p.patient.display_name]));
  const open = (impacts.data ?? []).filter((i) => i.state !== "closed");
  const closed = (impacts.data ?? []).filter((i) => i.state === "closed");
  return (
    <>
      <div className="page-head"><div><h1>Impact queue</h1><p>Protocol and source changes nominate review; they never change an individual plan by themselves.</p></div></div>
      {impacts.isLoading ? <Loading what="impact reviews" /> : null}
      <Card title={`Open impact reviews (${open.length})`} testId="impacts-open">
        {open.length ? open.map((i) => <ImpactItem key={i.id} workspaceId={workspaceId} impact={i} patientName={names.get(i.patient_id) ?? "Patient"} />) : <Empty>No open impact reviews.</Empty>}
      </Card>
      <Card title={`Closed impact reviews (${closed.length})`} testId="impacts-closed">
        {closed.length ? closed.map((i) => <ImpactItem key={i.id} workspaceId={workspaceId} impact={i} patientName={names.get(i.patient_id) ?? "Patient"} />) : <Empty>Nothing closed yet.</Empty>}
      </Card>
    </>
  );
}
