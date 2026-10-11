"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Card, Dialog, Empty, ErrorSummary, Meta, Select, TextArea, TextInput } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useMembers, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { day, relDay, when, words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";
import { PlanDecisionContext } from "./PlanDecisionContext";

type PlanView = Schemas["PlanView"];
type Draft = { applicability_id: string; exception_ids: string[]; intent: string; alternatives: string; rationale: string;
  obligation: { id: string; purpose: string; day: string; owner_username: string } };

function PlanEditor({ workspaceId, patientId, existing }: { workspaceId: string; patientId: string; existing: PlanView | null }) {
  const path = { workspace_id: workspaceId, patient_id: patientId };
  const reviews = useWs(workspaceId, ["patient", patientId, "applicability"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/applicability", { params: { path } }));
  const discussions = useWs(workspaceId, ["patient", patientId, "discussions"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/discussions", { params: { path } }));
  const exceptions = useWs(workspaceId, ["patient", patientId, "exceptions"], () => api.GET("/api/v1/workspaces/{workspace_id}/exceptions", { params: { path: { workspace_id: workspaceId }, query: { patient_id: patientId } } }));
  const members = useMembers(workspaceId);
  const action = useAction(workspaceId);
  const plan = existing?.plan;
  const first = (plan?.obligations?.[0] ?? null) as Record<string, any> | null;
  // Local draft state: kept on any failure. It is only replaced when the user explicitly reloads the server version.
  const [draft, setDraft] = useState<Draft>({
    applicability_id: plan?.applicability_id ?? "", exception_ids: (plan?.exception_ids as string[]) ?? [], intent: plan?.intent ?? "",
    alternatives: plan?.alternatives ?? "", rationale: plan?.rationale ?? "",
    obligation: { id: first?.id ?? "OBL-ROUTINE-REVIEW", purpose: first?.purpose ?? "Routine follow-up review", day: String(first?.due?.value ?? 14), owner_username: first?.owner_username ?? "mira" },
  });
  const [base, setBase] = useState(plan?.revision ?? 0);
  const accepted = (reviews.data ?? []).filter((r) => r.status === "accepted");
  const applicabilityId = draft.applicability_id || accepted[accepted.length - 1]?.id || "";
  const chosen = accepted.find((r) => r.id === applicabilityId);
  const latestDiscussion = discussions.data?.[discussions.data.length - 1];
  const usable = (exceptions.data ?? []).filter((e) => e.status !== "superseded" && e.protocol_version_id === chosen?.protocol_version_id);

  const content = () => ({
    applicability_id: applicabilityId, discussion_id: latestDiscussion?.id ?? null, exception_ids: draft.exception_ids.filter((id) => usable.some((e) => e.id === id)),
    intent: draft.intent, alternatives: draft.alternatives || null, rationale: draft.rationale || null,
    obligations: [{ id: draft.obligation.id, purpose: draft.obligation.purpose, due: relDay(Number(draft.obligation.day)), owner_username: draft.obligation.owner_username }],
  });
  async function save(): Promise<{ id: string; revision: number } | null> {
    const done = plan
      ? await action.run("save", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/plans/{plan_id}/save", {
        params: { path: { workspace_id: workspaceId, plan_id: plan.id } }, body: { command_id, expected_revision: base, ...content() } as never }), "Plan draft saved")
      : await action.run("start", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/plans", {
        params: { path }, body: { command_id, ...content() } as never }), "Plan draft created");
    if (!done?.target) return null;
    setBase(done.target.revision);
    return { id: done.target.id, revision: done.target.revision };
  }
  async function submit() {
    const saved = await save();
    if (!saved) return;
    await action.run("submit", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/plans/{plan_id}/submit", {
      params: { path: { workspace_id: workspaceId, plan_id: saved.id } }, body: { command_id, expected_revision: saved.revision } }), "Exact plan version frozen for signature");
  }

  return (
    <form data-testid="plan-editor" onSubmit={(e) => { e.preventDefault(); void save(); }}>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {reviews.isSuccess && discussions.isSuccess && (!accepted.length || !latestDiscussion) ? <div className="notice">
        <strong>Before this plan can be submitted</strong>
        <p className="small">Complete the relevant review and patient discussion. Your entries here stay in place while you switch views.</p>
        <div className="row">
          {!accepted.length ? <a href="#applicability">Review applicability</a> : null}
          {!latestDiscussion ? <a href="#discussion">Document patient discussion</a> : null}
        </div>
      </div> : null}
      <Select label="Accepted applicability review to pin" value={applicabilityId} onChange={(applicability_id) => setDraft({ ...draft, applicability_id })}
        options={accepted.length ? accepted.map((r) => ({ value: r.id, label: `Applicability review v${r.version_no}` })) : [{ value: "", label: "No accepted applicability review yet" }]} />
      <p className="small">Patient discussion pinned: {latestDiscussion ? `version ${latestDiscussion.version_no} (${latestDiscussion.recorded_by_name})` : "none documented — required before submission"}</p>
      {usable.length ? (
        <fieldset>
          <legend>Exceptions this plan relies on</legend>
          {usable.map((e) => (
            <label className="check" key={e.id}>
              <input type="checkbox" checked={draft.exception_ids.includes(e.id)} onChange={(ev) => setDraft({ ...draft, exception_ids: ev.target.checked ? [...draft.exception_ids, e.id] : draft.exception_ids.filter((x) => x !== e.id) })} />
              {e.requirement_id} — {e.exception_type} exception <Badge value={e.effective_status} />
            </label>
          ))}
        </fieldset>
      ) : null}
      <TextArea label="Individual intent" value={draft.intent} onChange={(intent) => setDraft({ ...draft, intent })} required
        hint="Documented individual intent for this patient. No dosing, eligibility threshold or treatment rule is entered or inferred here." />
      <TextArea label="Alternatives discussed" value={draft.alternatives} onChange={(alternatives) => setDraft({ ...draft, alternatives })} rows={2} />
      <TextArea label="Rationale" value={draft.rationale} onChange={(rationale) => setDraft({ ...draft, rationale })} rows={2} />
      <fieldset>
        <legend>Authored follow-up obligation</legend>
        <div className="grid grid-3">
          <TextInput label="Purpose" value={draft.obligation.purpose} onChange={(purpose) => setDraft({ ...draft, obligation: { ...draft.obligation, purpose } })} />
          <TextInput label="Due (relative day)" inputMode="numeric" value={draft.obligation.day} onChange={(d) => setDraft({ ...draft, obligation: { ...draft.obligation, day: d } })} />
          <Select label="Owner" value={draft.obligation.owner_username} onChange={(owner_username) => setDraft({ ...draft, obligation: { ...draft.obligation, owner_username } })}
            options={(members.data ?? []).map((m) => ({ value: m.username, label: m.display_name }))} />
        </div>
      </fieldset>
      <div className="row">
        <Button type="submit" busy={action.pending === "save" || action.pending === "start"}>{plan ? "Save draft" : "Create plan draft"}</Button>
        <Button variant="primary" busy={action.pending === "submit"} onClick={() => void submit()}>Save and submit for signature</Button>
      </div>
      <p className="small">Saving, submitting and signing are three separate server actions. Nothing is signed by saving.</p>
    </form>
  );
}

function Gates({ view }: { view: PlanView }) {
  return (
    <div className="table-wrap"><table data-testid="gates">
      <thead><tr><th>Requirement</th><th>Assessment</th><th>Approval gate</th></tr></thead>
      <tbody>{view.gates.map((g) => (
        <tr key={g.requirement_id}><td>{g.requirement_id}</td><td><Badge value={g.assessment ?? "pending"} /></td>
          <td>{g.satisfied ? <Badge value="approved" label={g.exception_id ? "covered by approved exception" : "satisfied"} /> : <><Badge value="blocked" /> <span className="small">{g.message}</span></>}</td></tr>
      ))}</tbody>
    </table></div>
  );
}

export function PlanPanel({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const plans = useWs(workspaceId, ["patient", patientId, "plans"], () =>
    api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/plans", { params: { path: { workspace_id: workspaceId, patient_id: patientId } } }));
  const action = useAction(workspaceId);
  const [signing, setSigning] = useState<PlanView | null>(null);
  const [startSuccessor, setStartSuccessor] = useState(false);
  const [disposition, setDisposition] = useState({ value: "held", reason: "" });
  const views = plans.data ?? [];
  const open = views.find((v) => ["draft", "submitted"].includes(v.plan.status)) ?? null;
  const current = [...views].reverse().find((v) => v.plan.status === "approved") ?? null;
  const history = views.filter((v) => v.plan.status === "superseded");
  const planPath = (id: string) => ({ workspace_id: workspaceId, plan_id: id });

  async function sign(view: PlanView) {
    const done = await action.run(`sign:${view.plan.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/plans/{plan_id}/approve", {
      params: { path: planPath(view.plan.id) }, body: { command_id, expected_revision: view.plan.revision, packet_id: view.packet!.id, digest: view.packet!.target_digest } }),
      `Plan version ${view.plan.version_no} approved`);
    if (done) setSigning(null);
  }

  return (
    <Card title="Individual plan" testId="plan">
      <ErrorSummary error={signing ? null : action.error} onDismiss={action.clearError} />
      {current ? (
        <div className="item" data-testid="plan-current">
          <div className="row">
            <strong>Plan version {current.plan.version_no}</strong><Badge value="approved" />
            <span data-testid="plan-disposition"><Badge value={current.disposition} label={`disposition: ${current.disposition}`} /></span>
            <span data-testid="plan-currency"><Badge value={current.currency.status} label={current.currency.status === "current" ? "review current" : "review needed"} /></span>
          </div>
          <p className="quote">{current.plan.intent}</p>
          <details><summary>Review the patient context and rationale behind this signed plan</summary><PlanDecisionContext workspaceId={workspaceId} view={current} /></details>
          <Meta items={[["Signed by", current.approval?.recorded_by_name], ["Signed", when(current.approval?.recorded_at)],
            ["Exact packet digest", <span className="mono" key="d" data-testid="plan-digest">{current.approval?.target_digest}</span>],
            ["Protocol version", <Link key="p" href={`/w/${workspaceId}/department/protocols/${current.plan.protocol_version_id}`}>Open pinned protocol version</Link>],
            ["Pinned inputs", `${current.approval?.read_set.length ?? 0} exact versions`], ["Exceptions", (current.plan.exception_ids as string[]).length || "none"]]} />
          <p className="small">{current.signature_notice}</p>
          {current.currency.reasons.length ? (
            <div className="card card-warn" data-testid="currency-reasons">
              <strong>Review needed — the signed plan stays in force while an owner reviews:</strong>
              <ul>{current.currency.reasons.map((r, i) => <li key={i}>Impact on {String(r.scope).split("/").slice(2).join("/") || String(r.scope)} — owner {String(r.owner)} ({words(String(r.state))})</li>)}</ul>
              <Link href={`/w/${workspaceId}/impacts`}>Open the impact queue</Link>
            </div>
          ) : null}
          <Gates view={current} />
          {can("plan.approve") ? (
            <details>
              <summary>Change disposition</summary>
              <div className="row" style={{ alignItems: "flex-end" }}>
                <Select label="Disposition" value={disposition.value} onChange={(value) => setDisposition({ ...disposition, value })} options={["held", "active", "completed"].map((v) => ({ value: v, label: v }))} />
                <TextInput label="Reason" value={disposition.reason} onChange={(reason) => setDisposition({ ...disposition, reason })} />
                <Button style={{ marginBottom: ".6rem" }} onClick={() => action.run("disposition", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/plans/{plan_id}/disposition", {
                  params: { path: planPath(current.plan.id) }, body: { command_id, expected_revision: current.plan.revision, disposition: disposition.value as never, reason: disposition.reason } }), "Disposition recorded")}>Record disposition</Button>
              </div>
            </details>
          ) : null}
        </div>
      ) : null}

      {open?.plan.status === "submitted" ? (
        <div className="item" data-testid="plan-submitted">
          <div className="row"><strong>Plan version {open.plan.version_no}</strong><Badge value="submitted" label="frozen for signature" /></div>
          <p className="quote">{open.plan.intent}</p>
          <Meta items={[["Frozen digest", <span className="mono" key="d">{open.packet?.target_digest}</span>], ["Pinned inputs", `${open.packet?.read_set.length ?? 0} exact versions`],
            ["Watched scopes", Object.keys((open.packet?.watch_set ?? {}) as object).length], ["Frozen by", open.packet?.author_name]]} />
          <Gates view={open} />
          {open.packet_changes.length ? (
            <div className="card card-warn" data-testid="packet-changes">
              <strong>Relevant material changed after this version was frozen.</strong>
              <ul>{open.packet_changes.map((c, i) => <li key={i}>{String(c.reason ?? `${String(c.scope).split("/").slice(2).join("/")} — ${String((c.last_change as Record<string, any>)?.event)} by ${String((c.last_change as Record<string, any>)?.actor)}`)}</li>)}</ul>
              <p className="small">The signature would be refused. Reopen the draft, review the change and re-submit.</p>
            </div>
          ) : null}
          {can("plan.author") ? (
            <div className="row">
              {can("plan.approve") ? <Button variant="primary" onClick={() => { action.clearError(); setSigning(open); }}>Review and sign…</Button> : null}
              <Button onClick={() => action.run("reopen", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/plans/{plan_id}/reopen", {
                params: { path: planPath(open.plan.id) }, body: { command_id, expected_revision: open.plan.revision } }), "Plan reopened as a draft")}>Reopen draft</Button>
            </div>
          ) : <p className="small">Awaiting the treating clinician&apos;s signature.</p>}
        </div>
      ) : null}

      {open?.plan.status === "draft" && can("plan.author") ? <div className="item"><strong>Draft plan version {open.plan.version_no}</strong><PlanEditor key={open.plan.id} workspaceId={workspaceId} patientId={patientId} existing={open} /></div> : null}
      {!open && can("plan.author") ? (
        current && !startSuccessor
          ? <Button onClick={() => setStartSuccessor(true)}>Draft a successor plan version</Button>
          : <div className="item"><strong>{current ? "Successor plan draft" : "New plan draft"}</strong><PlanEditor key="new" workspaceId={workspaceId} patientId={patientId} existing={null} /></div>
      ) : null}
      {!views.length && !can("plan.author") ? <Empty>No plan has been drafted for this patient.</Empty> : null}

      {history.length ? (
        <details data-testid="plan-history">
          <summary>Signed history ({history.length} superseded version{history.length > 1 ? "s" : ""})</summary>
          {history.map((v) => (
            <div className="item" key={v.plan.id}>
              <div className="row"><strong>Version {v.plan.version_no}</strong><Badge value="superseded" /><span className="small">signed by {v.approval?.recorded_by_name} · {when(v.approval?.recorded_at)}</span></div>
              <p className="quote">{v.plan.intent}</p><p className="small mono">{v.approval?.target_digest}</p>
            </div>
          ))}
        </details>
      ) : null}

      <Dialog open={!!signing} title="Sign this exact plan version" onClose={() => setSigning(null)}>
        {signing ? (
          <div data-testid="sign-dialog">
            <ErrorSummary error={action.error} />
            <p>You are signing exactly this frozen packet. The server re-checks every pinned input and watched scope when the signature is committed.</p>
            <p className="quote">{signing.plan.intent}</p>
            <PlanDecisionContext workspaceId={workspaceId} view={signing} />
            <Meta items={[["Plan version", signing.plan.version_no], ["Digest", <span className="mono" key="d">{signing.packet?.target_digest}</span>],
              ["Obligations", (signing.plan.obligations as Record<string, any>[]).map((o) => `${o.purpose} — ${day(o.due)} — ${o.owner_username}`).join("; ")]]} />
            <p className="small">{signing.signature_notice}</p>
            <div className="row">
              <Button variant="primary" busy={action.pending === `sign:${signing.plan.id}`} onClick={() => void sign(signing)}>Sign plan</Button>
              <Button onClick={() => setSigning(null)}>Cancel</Button>
            </div>
          </div>
        ) : null}
      </Dialog>
    </Card>
  );
}
