"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Select, TextInput } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useMembers, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { day, relDay, when, words } from "@/lib/format";
import { useSession, useWorkspace } from "@/lib/session/session";

type Task = Schemas["TaskOut"];

export function TaskBoard({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const { session } = useSession();
  const ws = { workspace_id: workspaceId };
  const tasks = useWs(workspaceId, ["patient", patientId, "tasks"], () => api.GET("/api/v1/workspaces/{workspace_id}/tasks", { params: { path: ws, query: { patient_id: patientId } } }));
  const plans = useWs(workspaceId, ["patient", patientId, "plans"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/plans", { params: { path: { ...ws, patient_id: patientId } } }));
  const sops = useWs(workspaceId, ["sops"], () => api.GET("/api/v1/workspaces/{workspace_id}/sops", { params: { path: ws } }));
  const members = useMembers(workspaceId);
  const action = useAction(workspaceId);
  const [owners, setOwners] = useState<Record<string, string>>({});
  const [text, setText] = useState<Record<string, string>>({});
  const [edit, setEdit] = useState<Record<string, { owner: string; due: string; note: string }>>({});
  const plan = [...(plans.data ?? [])].reverse().find((v) => v.plan.status === "approved");
  const sop = (sops.data ?? []).find((s) => s.selectable);
  const steps = (sop?.steps ?? []) as Record<string, any>[];
  const assignees = (members.data ?? []).filter((m) => m.capabilities.includes("task.act") || m.capabilities.includes("task.assign"));
  const defaultOwner = (role: string) => (role.toLowerCase().includes("coordinator") ? "mira" : "isha");

  const act = (task: Task, verb: "send" | "receive" | "accept", label: string) => action.run(`${verb}:${task.id}`, (command_id) =>
    api.POST(`/api/v1/workspaces/{workspace_id}/tasks/{task_id}/${verb}`, { params: { path: { ...ws, task_id: task.id } }, body: { command_id, expected_revision: task.revision } }), label);
  const withReason = (task: Task, verb: "return" | "block" | "cancel", label: string) => action.run(`${verb}:${task.id}`, (command_id) =>
    api.POST(`/api/v1/workspaces/{workspace_id}/tasks/{task_id}/${verb}`, { params: { path: { ...ws, task_id: task.id } }, body: { command_id, expected_revision: task.revision, reason: text[task.id] ?? "" } }), label);

  return (
    <Card title="Handoff tasks" testId="tasks">
      <p className="small">Tasks come from an exact SOP version. A sent handoff is not an accepted one, and completing a task records no treatment outcome.</p>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {can("task.assign") && plan && sop && !(tasks.data ?? []).some((t) => t.plan_version_id === plan.plan.id && t.sop_version_id === sop.id) ? (
        <fieldset data-testid="instantiate">
          <legend>Assign SOP work for plan v{plan.plan.version_no}</legend>
          <p className="small">From <Link href={`/w/${workspaceId}/department/sops/${sop.id}`}>{sop.title} v{sop.version_no}</Link></p>
          {steps.map((step) => (
            <div className="row" key={step.id}>
              <span style={{ flex: 1 }}>{step.title} <span className="small">({step.role}{step.requires?.length ? ` · requires ${step.requires.join(", ")}` : ""})</span></span>
              <select aria-label={`Owner for ${step.title}`} style={{ width: 220 }} value={owners[step.id] ?? defaultOwner(step.role)} onChange={(e) => setOwners({ ...owners, [step.id]: e.target.value })}>
                {assignees.map((m) => <option key={m.username} value={m.username}>{m.display_name}</option>)}
              </select>
            </div>
          ))}
          <Button variant="primary" busy={action.pending === "instantiate"} onClick={() => action.run("instantiate", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/plans/{plan_id}/tasks", {
            params: { path: { ...ws, plan_id: plan.plan.id } },
            body: { command_id, sop_version_id: sop.id, owners: Object.fromEntries(steps.map((s) => [s.id, owners[s.id] ?? defaultOwner(s.role)])), due: {} } }), "SOP tasks created")}>
            Create tasks from the SOP
          </Button>
        </fieldset>
      ) : null}
      {tasks.data?.length ? tasks.data.map((task) => {
        const mine = task.owner_id === session?.account.id && can("task.act");
        const blockedGate = task.gates.find((g) => !g.satisfied);
        const form = edit[task.id];
        return (
          <div className="item" key={task.id} data-testid={`task-${task.sop_step_id}`}>
            <div className="row"><strong>{task.action}</strong><span data-testid={`task-status-${task.sop_step_id}`}><Badge value={task.status} /></span>
              <span className="small">Owner: {task.owner_name ?? "unassigned"}{task.due ? ` · due ${day(task.due)}` : ""}</span></div>
            <p className="small">
              <Link href={`/w/${workspaceId}/department/sops/${task.sop_version_id}`} data-testid={`task-sop-link-${task.sop_step_id}`}>{task.sop_title} v{task.sop_version_no}</Link> · step {task.sop_step_id}
              {" · "}expected evidence: {task.expected_evidence}{task.note ? ` · note: ${task.note}` : ""}
            </p>
            {blockedGate ? <p className="small" data-testid={`task-gate-${task.sop_step_id}`}>⚠ Dispatch depends on {blockedGate.requirement_id}: {blockedGate.message} Other tasks are unaffected.</p> : null}
            {task.completion_evidence ? <p className="quote">Completion evidence: {String((task.completion_evidence as Record<string, any>).text)}</p> : null}
            <div className="row">
              {can("task.assign") && ["draft", "returned"].includes(task.status) ? <Button variant="primary" busy={action.pending === `send:${task.id}`} onClick={() => act(task, "send", "Handoff sent")}>Send handoff</Button> : null}
              {mine && task.status === "sent" ? <Button onClick={() => act(task, "receive", "Handoff received")}>Mark received</Button> : null}
              {mine && ["sent", "received", "blocked"].includes(task.status) ? <Button variant="primary" onClick={() => act(task, "accept", "Handoff accepted")}>Accept</Button> : null}
              {can("task.assign") && !["completed", "cancelled"].includes(task.status) ? (
                <Button onClick={() => setEdit({ ...edit, [task.id]: form ? (undefined as never) : { owner: "", due: task.due ? String((task.due as Record<string, any>).value) : "", note: task.note ?? "" } })}>
                  {form ? "Close edit" : "Edit owner / due"}
                </Button>
              ) : null}
            </div>
            {(mine && ["sent", "received", "accepted", "blocked"].includes(task.status)) ? (
              <div style={{ marginTop: ".4rem" }}>
                <TextInput label={`Reason or completion evidence for “${task.action}”`} value={text[task.id] ?? ""} onChange={(v) => setText({ ...text, [task.id]: v })} />
                <div className="row">
                  {task.status === "accepted" ? <Button variant="primary" onClick={() => action.run(`complete:${task.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/tasks/{task_id}/complete", {
                    params: { path: { ...ws, task_id: task.id } }, body: { command_id, expected_revision: task.revision, evidence: text[task.id] ?? "" } }), "Task completed with evidence")}>Complete with evidence</Button> : null}
                  <Button onClick={() => withReason(task, "return", "Handoff returned")}>Return</Button>
                  <Button onClick={() => withReason(task, "block", "Task marked blocked")}>Mark blocked</Button>
                </div>
              </div>
            ) : null}
            {form ? (
              <fieldset style={{ marginTop: ".4rem" }}>
                <legend>Administrative edit (does not affect any clinical review)</legend>
                <div className="grid grid-3">
                  <Select label="Owner" value={form.owner} onChange={(owner) => setEdit({ ...edit, [task.id]: { ...form, owner } })}
                    options={[{ value: "", label: "Keep current owner" }, ...assignees.map((m) => ({ value: m.username, label: m.display_name }))]} />
                  <TextInput label="Due (relative day)" inputMode="numeric" value={form.due} onChange={(due) => setEdit({ ...edit, [task.id]: { ...form, due } })} />
                  <TextInput label="Note" value={form.note} onChange={(note) => setEdit({ ...edit, [task.id]: { ...form, note } })} />
                </div>
                <Button busy={action.pending === `update:${task.id}`} onClick={async () => {
                  const done = await action.run(`update:${task.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/tasks/{task_id}/update", {
                    params: { path: { ...ws, task_id: task.id } },
                    body: { command_id, expected_revision: task.revision, owner_username: form.owner || null, due: form.due ? relDay(Number(form.due)) as never : null, note: form.note } }), "Task updated");
                  if (done) setEdit({ ...edit, [task.id]: undefined as never });
                }}>Save task changes</Button>
              </fieldset>
            ) : null}
            <details>
              <summary className="small">Handoff history ({task.events.length})</summary>
              <ul>{task.events.map((e) => <li key={e.id} className="small">{words(e.event)} — {e.recorded_by_name} · {when(e.recorded_at)}{e.reason ? ` — ${e.reason}` : ""}</li>)}</ul>
            </details>
          </div>
        );
      }) : <Empty>No tasks yet. A coordinator assigns SOP work once the plan is approved.</Empty>}
    </Card>
  );
}
