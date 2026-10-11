"use client";

import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Select, TextArea, TextInput } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useMembers, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { day, relDay, when, words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

type Obligation = Schemas["FollowUpObligationOut"];
type Form = { day: string; reason: string; decision: string; rationale: string; nextPurpose: string; nextDay: string; nextOwner: string; dueDay: string };
const BLANK: Form = { day: "", reason: "", decision: "continue_unchanged", rationale: "", nextPurpose: "Next routine follow-up review", nextDay: "", nextOwner: "mira", dueDay: "" };

export function FollowUpPanel({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const ws = { workspace_id: workspaceId };
  const obligations = useWs(workspaceId, ["patient", patientId, "follow-ups"], () => api.GET("/api/v1/workspaces/{workspace_id}/follow-ups", { params: { path: ws, query: { patient_id: patientId } } }));
  const members = useMembers(workspaceId);
  const action = useAction(workspaceId);
  const [forms, setForms] = useState<Record<string, Form>>({});
  const form = (o: Obligation) => forms[o.id] ?? BLANK;
  const set = (o: Obligation, patch: Partial<Form>) => setForms({ ...forms, [o.id]: { ...form(o), ...patch } });
  const op = (o: Obligation) => ({ params: { path: { ...ws, obligation_id: o.id } } });

  return (
    <Card title="Routine follow-up obligations" testId="follow-ups">
      <p className="small">A routine review is its own duty and needs no concern. An unchanged review keeps the same signed plan and records the next obligation. Nothing here infers discharge or outcome.</p>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {obligations.data?.length ? obligations.data.map((o) => {
        const f = form(o);
        const openState = !["fulfilled", "cancelled"].includes(o.state);
        return (
          <div className="item" key={o.id} data-testid={`follow-up-${o.state}`}>
            <div className="row"><strong>{o.purpose}</strong><Badge value={o.state} />{o.authored ? <Badge value="reviewed" label="authored by the signed plan" /> : <Badge value="draft" label="administrative" />}</div>
            <p className="small">Clinical timing: {day(o.due)} · appointment: {o.scheduled_time ? day(o.scheduled_time) : "not scheduled"} · owner {o.owner_name}</p>
            {o.pending_change ? <p className="small">⚠ A change to the authored clinical timing ({day((o.pending_change as Record<string, any>).due)}) is awaiting clinical review; the authored timing still stands.</p> : null}
            {o.decisions.map((d) => <p className="quote" key={d.id}>Encounter decision — {words(d.decision)} — {d.rationale} <span className="small">({d.recorded_by_name}, {when(d.recorded_at)})</span></p>)}
            {openState && can("followup.manage") ? (
              <fieldset>
                <legend>Scheduling (administrative)</legend>
                <div className="grid grid-3">
                  <TextInput label="Appointment (relative day)" inputMode="numeric" value={f.day} onChange={(d) => set(o, { day: d })} />
                  <TextInput label="Reason (for reschedule, miss, transfer)" value={f.reason} onChange={(reason) => set(o, { reason })} />
                  <TextInput label="Propose new clinical timing (day)" inputMode="numeric" value={f.dueDay} onChange={(dueDay) => set(o, { dueDay })} hint="Clinical: opens review by the treating clinician." />
                </div>
                <div className="row">
                  <Button disabled={!f.day} onClick={() => action.run(`schedule:${o.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/follow-ups/{obligation_id}/schedule", {
                    ...op(o), body: { command_id, expected_revision: o.revision, scheduled_time: relDay(Number(f.day)) as never, reason: f.reason || null } }), "Follow-up scheduled (no delivery recorded)")}>
                    {o.scheduled_time ? "Reschedule" : "Schedule"}
                  </Button>
                  <Button onClick={() => action.run(`miss:${o.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/follow-ups/{obligation_id}/miss", {
                    ...op(o), body: { command_id, expected_revision: o.revision, reason: f.reason } }), "Marked missed (outcome unknown)")}>Mark missed</Button>
                  {o.authored ? <Button disabled={!f.dueDay} onClick={() => action.run(`due:${o.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/follow-ups/{obligation_id}/propose-due-change", {
                    ...op(o), body: { command_id, expected_revision: o.revision, due: relDay(Number(f.dueDay)) as never, reason: f.reason } }), "Clinical timing change sent for clinician review")}>Request clinical timing change</Button> : null}
                </div>
              </fieldset>
            ) : null}
            {openState && can("followup.decide") ? (
              <fieldset data-testid="encounter-decision">
                <legend>Encounter decision (treating clinician)</legend>
                <Select label="Decision" value={f.decision} onChange={(decision) => set(o, { decision })}
                  options={[{ value: "continue_unchanged", label: "Continue the signed plan unchanged" }, { value: "revise", label: "Revise the plan (through plan approval)" },
                    { value: "more_information", label: "More information needed" }, { value: "unresolved", label: "Unresolved" }]} />
                <TextArea label="Rationale" value={f.rationale} onChange={(rationale) => set(o, { rationale })} rows={2} />
                {["continue_unchanged", "more_information"].includes(f.decision) ? (
                  <div className="grid grid-3">
                    <TextInput label="Next obligation purpose" value={f.nextPurpose} onChange={(nextPurpose) => set(o, { nextPurpose })} />
                    <TextInput label="Next clinical timing (day)" inputMode="numeric" value={f.nextDay} onChange={(nextDay) => set(o, { nextDay })} />
                    <Select label="Next owner" value={f.nextOwner} onChange={(nextOwner) => set(o, { nextOwner })} options={(members.data ?? []).map((m) => ({ value: m.username, label: m.display_name }))} />
                  </div>
                ) : null}
                <Button variant="primary" busy={action.pending === `decide:${o.id}`} onClick={async () => {
                  const done = await action.run(`decide:${o.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/follow-ups/{obligation_id}/decide", {
                    ...op(o), body: { command_id, expected_revision: o.revision, decision: f.decision as never, rationale: f.rationale,
                      actual_time: o.scheduled_time as never ?? null,
                      next: f.nextDay && ["continue_unchanged", "more_information"].includes(f.decision) ? { purpose: f.nextPurpose, due: relDay(Number(f.nextDay)) as never, owner_username: f.nextOwner } : null } }),
                    "Encounter decision recorded");
                  if (done) setForms({ ...forms, [o.id]: BLANK });
                }}>Record encounter decision</Button>
              </fieldset>
            ) : null}
            <details><summary className="small">History ({o.history.length})</summary>
              <ul>{(o.history as Record<string, any>[]).map((h, i) => <li className="small" key={i}>{words(String(h.event))} — {h.by}{h.reason ? ` — ${h.reason}` : ""}{h.outcome ? ` (outcome: ${h.outcome})` : ""}</li>)}</ul>
            </details>
          </div>
        );
      }) : <Empty>No follow-up obligation exists yet. One is created when a plan with an authored obligation is approved.</Empty>}
    </Card>
  );
}
