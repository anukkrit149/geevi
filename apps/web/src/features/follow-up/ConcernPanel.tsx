"use client";

import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Select, TextArea, TextInput } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useMembers, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { when } from "@/lib/format";
import { useSession, useWorkspace } from "@/lib/session/session";

type Concern = Schemas["ConcernOut"];

export function ConcernPanel({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const { session } = useSession();
  const ws = { workspace_id: workspaceId };
  const concerns = useWs(workspaceId, ["patient", patientId, "concerns"], () => api.GET("/api/v1/workspaces/{workspace_id}/concerns", { params: { path: ws, query: { patient_id: patientId } } }));
  const members = useMembers(workspaceId);
  const action = useAction(workspaceId);
  const [form, setForm] = useState({ narrative: "", attributed_to: "patient", owner_username: "isha" });
  const [text, setText] = useState<Record<string, string>>({});
  const cp = (c: Concern) => ({ params: { path: { ...ws, concern_id: c.id } } });

  return (
    <Card title="Concerns" testId="concerns">
      <p className="small">A concern is an attributed report. Acknowledging it is not a response, and no triage is inferred by the software.</p>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {concerns.data?.length ? concerns.data.map((c) => {
        const mine = c.owner_id === session?.account.id;
        return (
          <div className="item" key={c.id} data-testid="concern">
            <div className="row"><span data-testid="concern-status"><Badge value={c.status} /></span><span className="small">Reported by the {c.attributed_to} · owner {c.owner_name} · {c.responsible_service}</span></div>
            <p className="quote">{c.narrative}</p>
            {c.unresolved_duty ? <p className="small"><strong>Open duty:</strong> {c.unresolved_duty}</p> : null}
            <ul>{c.events.map((e) => <li className="small" key={e.id}>{e.event} — {e.recorded_by_name} · {when(e.recorded_at)}{e.narrative && e.event !== "reported" ? ` — ${e.narrative}` : ""}</li>)}</ul>
            {c.status !== "closed" ? (
              <div>
                {(can("concern.respond") && mine) || can("concern.review") ? <TextInput label="Response / review note" value={text[c.id] ?? ""} onChange={(v) => setText({ ...text, [c.id]: v })} /> : null}
                <div className="row">
                  {can("concern.respond") && c.status === "open" ? <Button onClick={() => action.run(`ack:${c.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/concerns/{concern_id}/acknowledge", {
                    ...cp(c), body: { command_id, expected_revision: c.revision } }), "Concern acknowledged (still awaiting a response)")}>Acknowledge</Button> : null}
                  {can("concern.respond") ? <Button variant="primary" onClick={() => action.run(`respond:${c.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/concerns/{concern_id}/respond", {
                    ...cp(c), body: { command_id, expected_revision: c.revision, narrative: text[c.id] ?? "" } }), "Response recorded")}>Record response</Button> : null}
                  {can("concern.respond") ? <Button onClick={() => action.run(`escalate:${c.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/concerns/{concern_id}/escalate", {
                    ...cp(c), body: { command_id, expected_revision: c.revision, narrative: text[c.id] ?? "", to_service: "Fictional AML clinician on call", owner_username: "rao" } }), "Concern escalated to the clinician on call")}>Escalate to clinician</Button> : null}
                  {can("concern.review") ? <Button onClick={() => action.run(`review:${c.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/concerns/{concern_id}/review", {
                    ...cp(c), body: { command_id, expected_revision: c.revision, narrative: text[c.id] ?? "", close: true } }), "Concern reviewed and closed")}>Review and close</Button> : null}
                  {can("concern.review") ? <Button onClick={() => action.run(`review-open:${c.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/concerns/{concern_id}/review", { ...cp(c), body: { command_id, expected_revision: c.revision, narrative: text[c.id] ?? "", close: false } }), "Clinical review recorded; concern remains open")}>Review and keep open</Button> : null}
                </div>
              </div>
            ) : null}
          </div>
        );
      }) : <Empty>No concerns have been reported.</Empty>}
      {can("concern.record") ? (
        <form onSubmit={async (e) => {
          e.preventDefault();
          const done = await action.run("concern", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/concerns", {
            params: { path: { ...ws, patient_id: patientId } }, body: { command_id, narrative: form.narrative, attributed_to: form.attributed_to as never, owner_username: form.owner_username } }), "Concern recorded");
          if (done) setForm({ ...form, narrative: "" });
        }}>
          <fieldset>
            <legend>Record a reported concern</legend>
            <TextArea label="Concern as reported" value={form.narrative} onChange={(narrative) => setForm({ ...form, narrative })} required rows={2} />
            <div className="grid grid-2">
              <Select label="Reported by" value={form.attributed_to} onChange={(attributed_to) => setForm({ ...form, attributed_to })}
                options={[{ value: "patient", label: "Patient" }, { value: "caregiver", label: "Caregiver" }, { value: "staff", label: "Staff" }]} />
              <Select label="Responsible owner" value={form.owner_username} onChange={(owner_username) => setForm({ ...form, owner_username })}
                options={(members.data ?? []).filter((m) => m.capabilities.includes("concern.respond") || m.capabilities.includes("concern.review")).map((m) => ({ value: m.username, label: m.display_name }))} />
            </div>
            <Button type="submit" busy={action.pending === "concern"}>Record concern</Button>
          </fieldset>
        </form>
      ) : null}
    </Card>
  );
}
