"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Card, Dialog, Empty, ErrorSummary, Loading, TextArea, TextInput } from "@/components/ui";
import { api } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { useWorkspace } from "@/lib/session/session";

export function PatientList({ workspaceId }: { workspaceId: string }) {
  const { can } = useWorkspace(workspaceId);
  const patients = useWs(workspaceId, ["patients"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients", { params: { path: { workspace_id: workspaceId } } }));
  const action = useAction(workspaceId);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ display_name: "", system: "geevi-demo-mrn", value: "", episode_title: "New AML presentation (fictional)", summary: "" });
  const set = (key: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [key]: value }));

  async function register() {
    const done = await action.run("register", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/patients", {
      params: { path: { workspace_id: workspaceId } },
      body: { command_id, display_name: form.display_name, identifiers: [{ system: form.system, value: form.value }], episode_title: form.episode_title, summary: form.summary || null },
    }), "Patient registered");
    if (done) {
      setOpen(false);
      setForm((f) => ({ ...f, display_name: "", value: "", summary: "" }));
    }
  }

  return (
    <>
      <div className="page-head">
        <div><h1>Patients</h1><p>Fictional patients only. Identity is by namespaced identifier, never by name alone.</p></div>
        {can("patient.register") ? <Button variant="primary" onClick={() => setOpen(true)}>Register patient</Button> : null}
      </div>
      {patients.isLoading ? <Loading what="patients" /> : null}
      <Card title="Patient list" testId="patient-list">
        {patients.data?.length ? patients.data.map(({ patient, identifiers, episodes }) => (
          <div className="item" key={patient.id}>
            <div className="row">
              <Link className="item-title" href={`/w/${workspaceId}/patients/${patient.id}`}>{patient.display_name}</Link>
              <Badge value={patient.data_label} />
              {episodes.map((e) => <Badge key={e.id} value={e.status} label={`Episode ${e.status.replace("_", " ")}`} />)}
            </div>
            <p className="small">{identifiers.map((i) => `${i.system}: ${i.value}`).join(" · ")} · {patient.summary}</p>
          </div>
        )) : <Empty>No patients are registered in this workspace yet.</Empty>}
      </Card>
      <Dialog open={open} title="Register patient" onClose={() => setOpen(false)}>
        <ErrorSummary error={action.error} />
        <form onSubmit={(e) => { e.preventDefault(); void register(); }}>
          <TextInput label="Display name" value={form.display_name} onChange={set("display_name")} required />
          <TextInput label="Identifier system (issuer namespace)" value={form.system} onChange={set("system")} required />
          <TextInput label="Identifier value" value={form.value} onChange={set("value")} required hint="Must be unique within its namespace." />
          <TextInput label="Episode title" value={form.episode_title} onChange={set("episode_title")} required />
          <TextArea label="Summary (optional)" value={form.summary} onChange={set("summary")} />
          <div className="row">
            <Button variant="primary" type="submit" busy={action.pending === "register"}>Register</Button>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}
