"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Loading, Select, TextInput } from "@/components/ui";
import { api } from "@/lib/api/client";
import { useMembers, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

export function PatientReportsReadiness({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const path = { workspace_id: workspaceId, patient_id: patientId };
  const profile = useWs(workspaceId, ["patient", patientId, "profile", ""], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/profile", { params: { path } }));
  const inputs = useWs(workspaceId, ["patient", patientId, "expected"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/expected-inputs", { params: { path } }));
  const reports = useWs(workspaceId, ["patient", patientId, "reports"], () => api.GET("/api/v1/workspaces/{workspace_id}/reports", { params: { path: { workspace_id: workspaceId }, query: { patient_id: patientId } } }));
  const members = useMembers(workspaceId);
  const action = useAction(workspaceId);
  const [expected, setExpected] = useState({ artifact: "", report_type: "molecular", owner_username: "mira", next_action: "" });
  const [link, setLink] = useState<Record<string, string>>({});
  if (profile.isLoading) return <Loading what="report review" />;
  if (!profile.data) return <p role="alert">Report review information could not be loaded.</p>;
  const pending = profile.data.unresolved.filter((u) => u.kind !== "expected_input");
  return <><ErrorSummary error={action.error} onDismiss={action.clearError} />
    <Card title="Reports awaiting verification" testId="report-review-queue">
      <p className="small">The coordinator checks identity and report findings here. Only source-verified findings appear in the clinical overview.</p>
      {pending.length ? pending.map((u, i) => <div className="item" key={i}><p>{u.text}</p><p className="small">{u.next_action}{u.target_kind === "source_document" ? <> · <Link href={`/w/${workspaceId}/patients/${patientId}/sources/${u.target_id}`}>Review report</Link></> : null}</p></div>) : <Empty>No reports awaiting verification.</Empty>}
    </Card>
        <Card title="Investigations and reports awaited" testId="expected-inputs">
          <p className="small">Record the report or investigation awaited, its owner and next action. This is a tracking record; it does not place a test order.</p>
          {inputs.data?.length ? inputs.data.map((item) => (
            <div className="item" key={item.id}>
              <div className="row"><strong>{item.artifact}</strong><Badge value={item.state} /></div>
              <p className="small">Owner: {item.owner_name} · Next: {item.next_action}</p>
              {can("source.import") && item.state !== "received" ? (
                <div className="row">
                  <select aria-label={`Report that fulfils ${item.artifact}`} value={link[item.id] ?? ""} onChange={(e) => setLink({ ...link, [item.id]: e.target.value })} style={{ maxWidth: 260 }}>
                    <option value="">Select the fulfilling report…</option>
                    {(reports.data ?? []).map((r) => <option key={r.id} value={r.id}>{r.accession} · {words(r.report_type ?? "")} v{r.version_no} ({r.issued_status})</option>)}
                  </select>
                  <Button disabled={!link[item.id]} onClick={() => action.run(`link:${item.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/expected-inputs/{item_id}/link-report", {
                    params: { path: { workspace_id: workspaceId, item_id: item.id } }, body: { command_id, expected_revision: item.revision, report_version_id: link[item.id] } }), "Expected input fulfilled by the linked report")}>Link report</Button>
                </div>
              ) : null}
            </div>
          )) : <Empty>No expected inputs recorded.</Empty>}
          {can("source.import") ? (
            <form onSubmit={async (e) => {
              e.preventDefault();
              const done = await action.run("expected", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/expected-inputs", {
                params: { path: { workspace_id: workspaceId } }, body: { command_id, patient_id: patientId, ...expected } }), "Expected input recorded");
              if (done) setExpected({ ...expected, artifact: "", next_action: "" });
            }}>
              <fieldset>
                <legend>Record an expected input</legend>
                <TextInput label="What is expected" value={expected.artifact} onChange={(artifact) => setExpected({ ...expected, artifact })} required />
                <TextInput label="Awaited report type" value={expected.report_type} onChange={(report_type) => setExpected({ ...expected, report_type })} required />
                <Select label="Owner" value={expected.owner_username} onChange={(owner_username) => setExpected({ ...expected, owner_username })}
                  options={(members.data ?? []).map((m) => ({ value: m.username, label: m.display_name }))} />
                <TextInput label="Next action" value={expected.next_action} onChange={(next_action) => setExpected({ ...expected, next_action })} required />
                <Button type="submit" busy={action.pending === "expected"}>Record expected input</Button>
              </fieldset>
            </form>
          ) : null}
        </Card>
  </>;
}
