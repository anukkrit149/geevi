"use client";

import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Select, TextArea, TextInput } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useScenario, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { when } from "@/lib/format";
import { useSession, useWorkspace } from "@/lib/session/session";

type Exception = Schemas["ExceptionRequestOut"];

export function ExceptionPanel({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const { session } = useSession();
  const exceptions = useWs(workspaceId, ["patient", patientId, "exceptions"], () =>
    api.GET("/api/v1/workspaces/{workspace_id}/exceptions", { params: { path: { workspace_id: workspaceId }, query: { patient_id: patientId } } }));
  const reviews = useWs(workspaceId, ["patient", patientId, "applicability"], () =>
    api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/applicability", { params: { path: { workspace_id: workspaceId, patient_id: patientId } } }));
  const protocols = useWs(workspaceId, ["protocols"], () => api.GET("/api/v1/workspaces/{workspace_id}/protocols", { params: { path: { workspace_id: workspaceId } } }));
  const scenario = useScenario();
  const action = useAction(workspaceId);
  const accepted = [...(reviews.data ?? [])].reverse().find((r) => r.status === "accepted");
  const protocol = protocols.data?.find((p) => p.id === accepted?.protocol_version_id);
  const requirements = (protocol?.requirements ?? []) as Record<string, any>[];
  const [form, setForm] = useState({ requirement_id: "", departure: "", rationale: "", review_trigger: "", expires_at: "" });
  const [rationale, setRationale] = useState<Record<string, string>>({});
  const requirementId = form.requirement_id || requirements.find((r) => r.waiver?.allowed)?.id || "";
  const requirement = requirements.find((r) => r.id === requirementId);

  function prefill() {
    const spec = Object.values((scenario.data?.exceptions ?? {}) as Record<string, any>).find((e) => e.requirement_id === requirementId);
    if (spec) setForm((f) => ({ ...f, departure: spec.departure, rationale: spec.rationale, review_trigger: f.review_trigger || "Review if the patient's circumstances change." }));
  }
  async function request() {
    if (!protocol || !requirement) return;
    const done = await action.run("request", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/exceptions", {
      params: { path: { workspace_id: workspaceId, patient_id: patientId } },
      body: { command_id, protocol_version_id: protocol.id, requirement_id: requirementId, exception_type: (requirement.waiver?.exception_type ?? "operational") as never,
        departure: form.departure, rationale: form.rationale, review_trigger: form.review_trigger || null, expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null },
    }), "Exception requested");
    if (done) setForm({ requirement_id: "", departure: "", rationale: "", review_trigger: "", expires_at: "" });
  }
  const decide = (e: Exception, decision: "approve" | "reject") => action.run(`decide:${e.id}`, (command_id) =>
    api.POST("/api/v1/workspaces/{workspace_id}/exceptions/{request_id}/decide", { params: { path: { workspace_id: workspaceId, request_id: e.id } },
      body: { command_id, expected_revision: e.revision, decision, rationale: rationale[e.id] ?? "" } }), `Exception decision recorded: ${decision}`);

  return (
    <Card title="Exceptions" testId="exceptions">
      <p className="small">An exception covers one requirement of one protocol version for this patient. It never changes the shared protocol and never approves a plan.</p>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {exceptions.data?.length ? exceptions.data.map((e) => {
        const capability = String((e.required_approvals as Record<string, any>).capability);
        const decided = e.decisions.some((d) => d.recorded_by === session?.account.id);
        return (
          <div className="item" key={e.id} data-testid={`exception-${e.requirement_id}-${e.effective_status}`}>
            <div className="row"><strong>{e.requirement_id}</strong><Badge value={e.exception_type === "clinical" ? "pending" : "reviewed"} label={`${e.exception_type} exception`} />
              <Badge value={e.effective_status} /><span className="small">v{e.version_no} · requested by {e.owner_name}</span></div>
            <p className="quote">{e.departure}</p>
            <p className="small">Rationale: {e.rationale}</p>
            <p className="small">{e.expires_at ? `Expires ${when(e.expires_at)}` : `Review trigger: ${e.review_trigger}`} · approvals {e.approvals_recorded} of {String((e.required_approvals as Record<string, any>).approvals)}</p>
            {e.decisions.map((d) => <p className="small" key={d.id}>{d.decision === "approve" ? "Approved" : "Rejected"} by {d.recorded_by_name} — {d.rationale}</p>)}
            {e.next_action ? <p className="small"><strong>Next:</strong> {e.next_action} (owner of the request: {e.owner_name})</p> : null}
            {e.effective_status === "pending" && can(capability) && !decided ? (
              <div>
                <TextInput label={`Decision rationale for ${e.requirement_id}`} value={rationale[e.id] ?? ""} onChange={(v) => setRationale({ ...rationale, [e.id]: v })} />
                <div className="row">
                  <Button variant="primary" busy={action.pending === `decide:${e.id}`} onClick={() => decide(e, "approve")}>Approve exception</Button>
                  <Button variant="danger" onClick={() => decide(e, "reject")}>Reject exception</Button>
                </div>
              </div>
            ) : null}
            {e.effective_status === "expired" && e.status === "approved" ? (
              <Button onClick={() => action.run(`expire:${e.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/exceptions/{request_id}/record-expiry", {
                params: { path: { workspace_id: workspaceId, request_id: e.id } }, body: { command_id, expected_revision: e.revision } }), "Expiry recorded; impact review nominated")}>Record expiry</Button>
            ) : null}
          </div>
        );
      }) : <Empty>No exception has been requested for this patient.</Empty>}
      {can("exception.request") && protocol ? (
        <form onSubmit={(e) => { e.preventDefault(); void request(); }} data-testid="exception-form">
          <fieldset>
            <legend>Request an exception</legend>
            <Select label="Requirement" value={requirementId} onChange={(requirement_id) => setForm({ ...form, requirement_id })}
              options={requirements.map((r) => ({ value: r.id, label: `${r.id} — ${r.waiver?.allowed ? `${r.waiver.exception_type} exception permitted` : "non-waivable"}` }))} />
            {scenario.data ? <Button variant="quiet" onClick={prefill}>Insert fictional scenario text</Button> : null}
            <TextArea label="Requested departure" value={form.departure} onChange={(departure) => setForm({ ...form, departure })} rows={2} required />
            <TextArea label="Rationale" value={form.rationale} onChange={(v) => setForm({ ...form, rationale: v })} rows={2} required />
            <div className="grid grid-2">
              <TextInput label="Review trigger" value={form.review_trigger} onChange={(review_trigger) => setForm({ ...form, review_trigger })} hint="Either a review trigger or an expiry is required." />
              <TextInput label="Expiry (optional)" type="datetime-local" value={form.expires_at} onChange={(expires_at) => setForm({ ...form, expires_at })} />
            </div>
            <Button type="submit" busy={action.pending === "request"}>Request exception</Button>
          </fieldset>
        </form>
      ) : null}
    </Card>
  );
}
