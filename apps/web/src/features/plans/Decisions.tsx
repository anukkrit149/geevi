"use client";

import { useState } from "react";
import { Button, Card, Empty, ErrorSummary, Select, TextArea, TextInput } from "@/components/ui";
import { WorkflowViews } from "@/components/workflow-views";
import { ExceptionPanel } from "@/features/exceptions/ExceptionPanel";
import { api } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { when } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";
import { ApplicabilityReview } from "./ApplicabilityReview";
import { PlanPanel } from "./PlanPanel";

function DiscussionPanel({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const path = { workspace_id: workspaceId, patient_id: patientId };
  const discussions = useWs(workspaceId, ["patient", patientId, "discussions"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/discussions", { params: { path } }));
  const action = useAction(workspaceId);
  const [form, setForm] = useState({ participants: "", attributed_to: "patient", goals: "", preferences: "" });
  const latest = discussions.data?.[discussions.data.length - 1];
  return (
    <Card title="Patient discussion" testId="discussion">
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {latest ? (
        <div className="item">
          <p className="quote">{latest.goals}</p>
          {latest.preferences ? <p className="small">Preferences: {latest.preferences}</p> : null}
          <p className="small">Version {latest.version_no} · attributed to the {latest.attributed_to} · participants: {(latest.participants as string[]).join(", ")} · entered by {latest.recorded_by_name} · {when(latest.recorded_at)}</p>
        </div>
      ) : <Empty>No patient discussion is documented yet.</Empty>}
      {can("discussion.record") ? (
        <form onSubmit={async (e) => {
          e.preventDefault();
          const done = await action.run("discussion", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/discussions", {
            params: { path }, body: { command_id, participants: form.participants.split(",").map((s) => s.trim()).filter(Boolean), attributed_to: form.attributed_to as never,
              goals: form.goals, preferences: form.preferences || null } }), "Patient discussion documented");
          if (done) setForm({ participants: "", attributed_to: "patient", goals: "", preferences: "" });
        }}>
          <fieldset>
            <legend>{latest ? "Document a new discussion version" : "Document the discussion"}</legend>
            <div className="grid grid-2">
              <TextInput label="Participants (comma separated)" value={form.participants} onChange={(participants) => setForm({ ...form, participants })} required />
              <Select label="Goals are attributed to" value={form.attributed_to} onChange={(attributed_to) => setForm({ ...form, attributed_to })}
                options={[{ value: "patient", label: "Patient" }, { value: "caregiver", label: "Caregiver" }]} />
            </div>
            <TextArea label="Goals in the patient's or caregiver's words" value={form.goals} onChange={(goals) => setForm({ ...form, goals })} required />
            <TextArea label="Preferences and practical constraints" value={form.preferences} onChange={(preferences) => setForm({ ...form, preferences })} rows={2} />
            <Button type="submit" busy={action.pending === "discussion"}>Document discussion</Button>
          </fieldset>
        </form>
      ) : null}
    </Card>
  );
}

export function Decisions({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const props = { workspaceId, patientId };
  return <WorkflowViews label="Plan workflow" initial="plan" views={[
    { id: "plan", label: "Individual plan", content: <PlanPanel {...props} /> },
    { id: "applicability", label: "Applicability", content: <ApplicabilityReview {...props} /> },
    { id: "discussion", label: "Patient discussion", content: <DiscussionPanel {...props} /> },
    { id: "exceptions", label: "Exceptions", content: <ExceptionPanel {...props} /> },
  ]} />;
}
