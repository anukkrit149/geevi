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

type Protocol = Schemas["ProtocolVersionOut"];
type Requirement = { id: string; kind: string; text: string; gate: string; waiver: { allowed: boolean; exception_type?: string | null }; watch: string[]; branch?: Record<string, string> | null; note?: string | null };

function Editor({ workspaceId, version }: { workspaceId: string; version: Protocol }) {
  const scenario = useScenario();
  const appraisals = useWs(workspaceId, ["appraisals", "accepted"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/appraisals", { params: { path: { workspace_id: workspaceId }, query: { status: "accepted" } } }));
  const action = useAction(workspaceId);
  const [draft, setDraft] = useState({ title: version.title, scope: version.scope, summary: version.summary ?? "", requirements: version.requirements as Requirement[], evidence: version.evidence as string[] });
  const [base, setBase] = useState(version.revision);
  const setReq = (i: number, patch: Partial<Requirement>) => setDraft((d) => ({ ...d, requirements: d.requirements.map((r, j) => (j === i ? { ...r, ...patch } : r)) }));

  async function save(): Promise<number | null> {
    const done = await action.run("save", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/protocols/{version_id}/save", {
      params: { path: { workspace_id: workspaceId, version_id: version.id } }, body: { command_id, expected_revision: base, ...draft, summary: draft.summary || null } as never }), "Protocol draft saved");
    if (!done?.target) return null;
    setBase(done.target.revision);
    return done.target.revision;
  }
  const insert = (which: "v1" | "v2") => {
    const spec = scenario.data?.protocol;
    if (spec) setDraft((d) => ({ ...d, title: spec.title, scope: spec.scope, summary: spec[which].summary, requirements: spec[which].requirements }));
  };

  return (
    <Card title="Draft content" testId="protocol-editor">
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {scenario.data ? (
        <div className="row">
          <Button variant="quiet" onClick={() => insert("v1")}>Insert fictional pathway requirements (v1)</Button>
          <Button variant="quiet" onClick={() => insert("v2")}>Insert fictional pathway requirements (v2)</Button>
        </div>
      ) : null}
      <TextInput label="Title" value={draft.title} onChange={(title) => setDraft({ ...draft, title })} />
      <TextArea label="Scope" value={draft.scope} onChange={(scope) => setDraft({ ...draft, scope })} rows={2} />
      <TextInput label="Summary of this version" value={draft.summary} onChange={(summary) => setDraft({ ...draft, summary })} />
      <h3>Requirements ({draft.requirements.length})</h3>
      <p className="small">Workflow requirements only. Do not enter clinical eligibility, dosing or therapy rules. Requirements are non-waivable unless an exception type is named.</p>
      {draft.requirements.map((r, i) => (
        <fieldset key={i} data-testid={`requirement-${r.id}`}>
          <legend>{r.id || `Requirement ${i + 1}`}</legend>
          <div className="grid grid-3">
            <TextInput label="Stable identifier" value={r.id} onChange={(id) => setReq(i, { id })} />
            <TextInput label="Kind" value={r.kind} onChange={(kind) => setReq(i, { kind })} hint="identity · context · discussion · operational · clinical_input" />
            <TextInput label="Gate" value={r.gate} onChange={(gate) => setReq(i, { gate })} hint="plan_approval or step:STEP-ID" />
          </div>
          <TextArea label="Requirement text" value={r.text} onChange={(text) => setReq(i, { text })} rows={2} />
          <div className="grid grid-2">
            <TextInput label="Permitted exception type (blank = non-waivable)" value={r.waiver?.allowed ? r.waiver.exception_type ?? "" : ""}
              onChange={(v) => setReq(i, { waiver: v ? { allowed: true, exception_type: v } : { allowed: false } })} />
            <TextInput label="Watched scopes (comma separated)" value={(r.watch ?? []).join(", ")} onChange={(v) => setReq(i, { watch: v.split(",").map((s) => s.trim()).filter(Boolean) })} />
          </div>
          <Button variant="quiet" onClick={() => setDraft((d) => ({ ...d, requirements: d.requirements.filter((_, j) => j !== i) }))}>Remove requirement</Button>
        </fieldset>
      ))}
      <Button onClick={() => setDraft((d) => ({ ...d, requirements: [...d.requirements, { id: "", kind: "operational", text: "", gate: "plan_approval", waiver: { allowed: false }, watch: [] }] }))}>Add requirement</Button>
      <fieldset style={{ marginTop: ".8rem" }} data-testid="evidence-picker">
        <legend>Supporting evidence (accepted appraisals only)</legend>
        {appraisals.data?.length ? appraisals.data.map((a) => (
          <label className="check" key={a.id}>
            <input type="checkbox" checked={draft.evidence.includes(a.id)} onChange={(e) => setDraft((d) => ({ ...d, evidence: e.target.checked ? [...d.evidence, a.id] : d.evidence.filter((x) => x !== a.id) }))} />
            Accepted appraisal v{a.version_no}: {String((a.content as Record<string, any>).findings ?? "").slice(0, 110)}
          </label>
        )) : <p className="small">No accepted appraisal exists yet. Evidence is accepted in Research, separately from publishing a protocol.</p>}
      </fieldset>
      <div className="row"><Button busy={action.pending === "save"} onClick={() => void save()}>Save draft</Button></div>
      <PublicationBar workspaceId={workspaceId} kind="protocols" version={{ ...version, revision: base }} onBeforeSubmit={save} />
    </Card>
  );
}

export function ProtocolDetail({ workspaceId, versionId }: { workspaceId: string; versionId: string }) {
  const { can } = useWorkspace(workspaceId);
  const { session } = useSession();
  const detail = useWs(workspaceId, ["protocol", versionId], () => api.GET("/api/v1/workspaces/{workspace_id}/protocols/{version_id}", { params: { path: { workspace_id: workspaceId, version_id: versionId } } }));
  const appraisals = useWs(workspaceId, ["appraisals", "all"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/appraisals", { params: { path: { workspace_id: workspaceId } } }));
  if (detail.isLoading) return <Loading what="protocol version" />;
  if (!detail.data) return <div className="card" role="alert" data-testid="record-unavailable"><h1>Record not available</h1><p>This protocol version does not exist in this workspace.</p></div>;
  const { version: v, family, reviews, publications, proposal } = detail.data;
  const editable = v.status === "draft" && v.recorded_by === session?.account.id && can("protocol.author");

  return (
    <>
      <div className="page-head">
        <div><h1>{v.title}</h1><p>Shared departmental protocol · version {v.version_no} · owner {v.owner_name}</p></div>
        <div className="row"><span data-testid="lifecycle"><Badge value={v.lifecycle} label={v.lifecycle === "published" ? "published · not yet effective" : words(v.lifecycle)} /></span>
          {v.review_due_reached ? <Badge value="pending" label="review due (still effective)" /> : null}</div>
      </div>
      <p className="small">{detail.data.validation_notice}</p>
      <Card title="Version record" testId="protocol-record">
        <Meta items={[["Approved", when(v.approved_at)], ["Published", when(v.published_at)], ["Effective from", when(v.effective_from)], ["Review due", when(v.review_due)],
          ["Withdrawn", v.withdrawn_at ? `${when(v.withdrawn_at)} — ${v.withdrawn_reason}` : null], ["Content digest", <span className="mono" key="d">{v.content_digest ?? "not yet frozen"}</span>]]} />
        <p className="small">Versions: {family.map((f) => (
          <span key={f.id}>{f.id === v.id ? <strong>v{f.version_no} ({words(f.lifecycle)})</strong> : <Link href={`/w/${workspaceId}/department/protocols/${f.id}`}>v{f.version_no} ({words(f.lifecycle)})</Link>}{" · "}</span>
        ))}</p>
        {proposal ? <p className="small" data-testid="proposal">Change proposal ({proposal.status}): {proposal.rationale}{Object.keys((proposal.diff ?? {}) as object).length ? ` · changed: ${Object.keys(proposal.diff as object).join(", ")}` : ""}</p> : null}
      </Card>
      {editable ? <Editor key={v.id} workspaceId={workspaceId} version={v} /> : (
        <Card title={`Requirements (${v.requirements.length})`} testId="requirements">
          <p>{v.scope}</p>
          <div className="table-wrap"><table>
            <thead><tr><th>ID</th><th>Requirement</th><th>Gate</th><th>Waiver</th></tr></thead>
            <tbody>{(v.requirements as Requirement[]).map((r) => (
              <tr key={r.id}><td className="mono">{r.id}</td><td>{r.text}{r.branch ? <div className="small">Branch — default: {r.branch.default}; alternate: {r.branch.alternate}</div> : null}</td>
                <td>{r.gate}</td><td>{r.waiver?.allowed ? <Badge value="pending" label={`${r.waiver.exception_type} exception permitted`} /> : <Badge value="superseded" label="non-waivable" />}</td></tr>
            ))}</tbody>
          </table></div>
          <p className="small">Supporting evidence: {v.evidence.length} accepted appraisal version(s).</p>
          {(appraisals.data ?? []).filter((a) => (v.evidence as string[]).includes(a.id)).map((a) => <p key={a.id}><Link href={`/w/${workspaceId}/research/${a.question_id}`}>Read supporting appraisal v{a.version_no} and its citations</Link> · {String((a.content as Record<string, unknown>).findings ?? "")}{a.review_needed ? <Badge value="review_needed" /> : null}</p>)}
          <PublicationBar workspaceId={workspaceId} kind="protocols" version={v} evidence={v.evidence as string[]} />
        </Card>
      )}
      <Card title="Independent review" testId="reviews"><ReviewPanel workspaceId={workspaceId} reviews={reviews} /></Card>
      <Card title="Publication decisions" testId="publications">
        {publications.length ? publications.map((p) => (
          <p key={p.id} className="small">{p.decision === "publish" ? "Published" : "Withdrawn"} by {p.recorded_by_name} · {when(p.recorded_at)}{p.effective_from ? ` · effective ${when(p.effective_from)}` : ""}{p.note ? ` — ${p.note}` : ""}</p>
        )) : <p className="small">No publication decision recorded.</p>}
      </Card>
    </>
  );
}
