"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Card, ErrorSummary, Loading, Meta, TextArea, TextInput } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useScenario, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { when, words } from "@/lib/format";
import { useSession, useWorkspace } from "@/lib/session/session";
import { PublicationBar } from "./PublicationBar";
import { ReviewPanel } from "./ReviewPanel";

type Sop = Schemas["SopVersionOut"];
type Step = { id: string; title: string; role: string; expected_evidence: string; depends_on: string[]; requires: string[] };

function Editor({ workspaceId, version }: { workspaceId: string; version: Sop }) {
  const scenario = useScenario();
  const action = useAction(workspaceId);
  const [draft, setDraft] = useState({ title: version.title, purpose: version.purpose, escalation: version.escalation, steps: version.steps as Step[] });
  const [base, setBase] = useState(version.revision);
  const setStep = (i: number, patch: Partial<Step>) => setDraft((d) => ({ ...d, steps: d.steps.map((s, j) => (j === i ? { ...s, ...patch } : s)) }));
  const list = (v: string) => v.split(",").map((s) => s.trim()).filter(Boolean);
  async function save(): Promise<number | null> {
    const done = await action.run("save", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/sops/{version_id}/save", {
      params: { path: { workspace_id: workspaceId, version_id: version.id } },
      body: { command_id, expected_revision: base, ...draft, protocol_version_id: version.protocol_version_id ?? null } as never }), "SOP draft saved");
    if (!done?.target) return null;
    setBase(done.target.revision);
    return done.target.revision;
  }
  return (
    <Card title="Draft content" testId="sop-editor">
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {scenario.data ? <Button variant="quiet" onClick={() => { const s = scenario.data!.sop; setDraft({ title: s.title, purpose: s.purpose, escalation: s.escalation, steps: s.steps.map((x: Partial<Step>) => ({ ...x, depends_on: x.depends_on ?? [], requires: x.requires ?? [] })) as Step[] }); }}>Insert fictional SOP steps</Button> : null}
      <TextInput label="Title" value={draft.title} onChange={(title) => setDraft({ ...draft, title })} />
      <TextArea label="Purpose" value={draft.purpose} onChange={(purpose) => setDraft({ ...draft, purpose })} rows={2} />
      <TextInput label="Escalation destination" value={draft.escalation} onChange={(escalation) => setDraft({ ...draft, escalation })} />
      <h3>Role-owned steps ({draft.steps.length})</h3>
      <p className="small">Steps create task specifications for the team. They are not clinical orders.</p>
      {draft.steps.map((s, i) => (
        <fieldset key={i}>
          <legend>{s.id || `Step ${i + 1}`}</legend>
          <div className="grid grid-3">
            <TextInput label="Step identifier" value={s.id} onChange={(id) => setStep(i, { id })} />
            <TextInput label="Step title" value={s.title} onChange={(title) => setStep(i, { title })} />
            <TextInput label="Owning role" value={s.role} onChange={(role) => setStep(i, { role })} />
            <TextInput label="Expected completion evidence" value={s.expected_evidence} onChange={(expected_evidence) => setStep(i, { expected_evidence })} />
            <TextInput label="Depends on steps" value={(s.depends_on ?? []).join(", ")} onChange={(v) => setStep(i, { depends_on: list(v) })} />
            <TextInput label="Gated by protocol requirements" value={(s.requires ?? []).join(", ")} onChange={(v) => setStep(i, { requires: list(v) })} />
          </div>
          <Button variant="quiet" onClick={() => setDraft((d) => ({ ...d, steps: d.steps.filter((_, j) => j !== i) }))}>Remove step</Button>
        </fieldset>
      ))}
      <Button onClick={() => setDraft((d) => ({ ...d, steps: [...d.steps, { id: "", title: "", role: "", expected_evidence: "", depends_on: [], requires: [] }] }))}>Add step</Button>
      <div className="row" style={{ marginTop: ".6rem" }}><Button busy={action.pending === "save"} onClick={() => void save()}>Save draft</Button></div>
      <PublicationBar workspaceId={workspaceId} kind="sops" version={{ ...version, revision: base }} onBeforeSubmit={save} />
    </Card>
  );
}

export function SopDetail({ workspaceId, versionId }: { workspaceId: string; versionId: string }) {
  const { can } = useWorkspace(workspaceId);
  const { session } = useSession();
  const detail = useWs(workspaceId, ["sop", versionId], () => api.GET("/api/v1/workspaces/{workspace_id}/sops/{version_id}", { params: { path: { workspace_id: workspaceId, version_id: versionId } } }));
  if (detail.isLoading) return <Loading what="SOP version" />;
  if (!detail.data) return <div className="card" role="alert" data-testid="record-unavailable"><h1>Record not available</h1><p>This SOP version does not exist in this workspace.</p></div>;
  const { version: v, family, reviews, publications } = detail.data;
  const editable = v.status === "draft" && v.recorded_by === session?.account.id && can("sop.author");
  return (
    <>
      <div className="page-head">
        <div><h1>{v.title}</h1><p>Departmental SOP · version {v.version_no} · owner {v.owner_name}</p></div>
        <span data-testid="lifecycle"><Badge value={v.lifecycle} label={words(v.lifecycle)} /></span>
      </div>
      <Card title="Version record" testId="sop-record">
        <p>{v.purpose}</p>
        <Meta items={[["Escalation destination", v.escalation], ["Approved", when(v.approved_at)], ["Published", when(v.published_at)], ["Effective from", when(v.effective_from)],
          ["Related protocol version", v.protocol_version_id ? <Link key="p" href={`/w/${workspaceId}/department/protocols/${v.protocol_version_id}`}>Open protocol version</Link> : "none"]]} />
        <p className="small">Versions: {family.map((f) => (
          <span key={f.id}>{f.id === v.id ? <strong>v{f.version_no} ({words(f.lifecycle)})</strong> : <Link href={`/w/${workspaceId}/department/sops/${f.id}`}>v{f.version_no} ({words(f.lifecycle)})</Link>}{" · "}</span>
        ))}</p>
      </Card>
      {editable ? <Editor key={v.id} workspaceId={workspaceId} version={v} /> : (
        <Card title={`Steps (${v.steps.length})`} testId="sop-steps">
          <div className="table-wrap"><table>
            <thead><tr><th>Step</th><th>Owning role</th><th>Expected completion evidence</th><th>Dependencies</th></tr></thead>
            <tbody>{(v.steps as Step[]).map((s) => (
              <tr key={s.id} data-testid={`step-${s.id}`}><td><strong>{s.title}</strong><div className="small mono">{s.id}</div></td><td>{s.role}</td><td>{s.expected_evidence}</td>
                <td className="small">{[...(s.depends_on ?? []).map((d) => `after ${d}`), ...(s.requires ?? []).map((r) => `gated by ${r}`)].join("; ") || "—"}</td></tr>
            ))}</tbody>
          </table></div>
          <PublicationBar workspaceId={workspaceId} kind="sops" version={v} />
        </Card>
      )}
      <Card title="Independent review" testId="reviews"><ReviewPanel workspaceId={workspaceId} reviews={reviews} /></Card>
      <Card title="Publication decisions" testId="publications">
        {publications.length ? publications.map((p) => <p key={p.id} className="small">{p.decision === "publish" ? "Published" : "Withdrawn"} by {p.recorded_by_name} · {when(p.recorded_at)}</p>) : <p className="small">No publication decision recorded.</p>}
      </Card>
    </>
  );
}
