"use client";

import Link from "next/link";
import { ArrowUpRight, Plus, MagnifyingGlass } from "@phosphor-icons/react";
import { Initials } from "@/components/brand";
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
  const [search, setSearch] = useState("");
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

  const matches = patients.data?.filter(({ patient, identifiers, episodes }) => [patient.display_name, patient.summary, ...identifiers.map((i) => i.value), ...episodes.map((e) => e.title)].join(" ").toLowerCase().includes(search.toLowerCase())) ?? [];
  return (
    <>
      <div className="page-head">
        <div><h1>Patients</h1><p>Open a patient to review their story, source reports and next decision.</p></div>
        {can("patient.register") ? <Button variant="primary" onClick={() => setOpen(true)}><Plus aria-hidden="true" />Register patient</Button> : null}
      </div>
      {patients.isLoading ? <Loading what="patients" /> : null}
      {patients.error ? <div className="error-summary" role="alert"><p>Patients could not be loaded.</p><Button onClick={() => patients.refetch()}>Try again</Button></div> : null}
      <Card title="Patient list" testId="patient-list">
        <div className="list-toolbar"><TextInput label="Find a patient" value={search} onChange={setSearch} placeholder="Name, identifier or episode" hint="Search name, identifier, referral summary or episode." /><span className="list-count" role="status">{patients.data ? `${matches.length} of ${patients.data.length} patients` : "Loading patients"}</span></div>
        {matches.map(({ patient, identifiers, episodes }) => <Link className="item patient-list-row" key={patient.id} href={`/w/${workspaceId}/patients/${patient.id}`} aria-label={patient.display_name}>
          <Initials name={patient.display_name} />
          <div><div className="row"><strong className="item-title">{patient.display_name}</strong>{episodes.map((e) => <Badge key={e.id} value={e.status} label={`Episode ${e.status.replace("_", " ")}`} />)}</div>
            <p className="small">{identifiers.map((i) => `${i.system}: ${i.value}`).join(" · ")}</p><p className="small">{patient.summary}</p>
          </div>
          <span className="icon-button" aria-hidden="true"><ArrowUpRight /></span>
        </Link>)}
        {patients.data && !matches.length ? <div className="empty-state"><MagnifyingGlass aria-hidden="true" /><h3>{search ? "No matching patients" : "Your patient list starts here"}</h3><Empty>{search ? "Try a different name, identifier or episode." : "No patients are registered in this workspace yet."}</Empty>{search ? <Button onClick={() => setSearch("")}>Clear search</Button> : null}</div> : null}
        <p className="hint">Fictional patients only. Identity is by namespaced identifier, never by name alone.</p>
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
