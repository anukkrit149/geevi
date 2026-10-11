"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Badge, Button, Card, Empty, ErrorSummary } from "@/components/ui";
import { api } from "@/lib/api/client";
import { useScenario, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { when, words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

export function DepartmentHome({ workspaceId }: { workspaceId: string }) {
  const { can } = useWorkspace(workspaceId);
  const router = useRouter();
  const ws = { workspace_id: workspaceId };
  const protocols = useWs(workspaceId, ["protocols"], () => api.GET("/api/v1/workspaces/{workspace_id}/protocols", { params: { path: ws } }));
  const sops = useWs(workspaceId, ["sops"], () => api.GET("/api/v1/workspaces/{workspace_id}/sops", { params: { path: ws } }));
  const work = useWs(workspaceId, ["work-items"], () => api.GET("/api/v1/workspaces/{workspace_id}/work-items", { params: { path: ws } }));
  const scenario = useScenario();
  const action = useAction(workspaceId);
  const s = scenario.data;

  async function newProtocol() {
    const done = await action.run("new-protocol", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/protocols", { params: { path: ws },
      body: { command_id, title: s?.protocol?.title ?? "Untitled departmental protocol", scope: s?.protocol?.scope ?? "Scope to be written", summary: s?.protocol?.v1?.summary ?? null,
        requirements: s?.protocol?.v1?.requirements ?? [], evidence: [] } }), "Protocol draft created");
    if (done?.target) router.push(`/w/${workspaceId}/department/protocols/${done.target.id}`);
  }
  async function newSop() {
    const effective = protocols.data?.find((p) => p.selectable);
    const done = await action.run("new-sop", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/sops", { params: { path: ws },
      body: { command_id, title: s?.sop?.title ?? "Untitled departmental SOP", purpose: s?.sop?.purpose ?? "Purpose to be written", escalation: s?.sop?.escalation ?? "Escalation desk",
        steps: s?.sop?.steps ?? [], protocol_version_id: effective?.id ?? null } }), "SOP draft created");
    if (done?.target) router.push(`/w/${workspaceId}/department/sops/${done.target.id}`);
  }

  return (
    <>
      <div className="page-head"><div><h1>Department</h1><p>Shared protocols and the separate operational SOP. Approval, publication and effect are distinct recorded states.</p></div></div>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      <Card title="Departmental protocols" testId="protocols" actions={can("protocol.author") ? <Button variant="primary" busy={action.pending === "new-protocol"} onClick={newProtocol}>New protocol draft{s ? " (fictional pathway)" : ""}</Button> : null}>
        {protocols.data?.length ? protocols.data.map((p) => (
          <div className="item" key={p.id}>
            <div className="row"><Link className="item-title" href={`/w/${workspaceId}/department/protocols/${p.id}`}>{p.title} — v{p.version_no}</Link><Badge value={p.lifecycle} label={words(p.lifecycle)} /></div>
            <p className="small">{p.requirements.length} requirements · owner {p.owner_name}{p.effective_from ? ` · effective ${when(p.effective_from)}` : ""}</p>
          </div>
        )) : <Empty>No protocol versions yet.</Empty>}
      </Card>
      <Card title="Standard operating procedures" testId="sops" actions={can("sop.author") ? <Button variant="primary" busy={action.pending === "new-sop"} onClick={newSop}>New SOP draft{s ? " (fictional steps)" : ""}</Button> : null}>
        {sops.data?.length ? sops.data.map((p) => (
          <div className="item" key={p.id}>
            <div className="row"><Link className="item-title" href={`/w/${workspaceId}/department/sops/${p.id}`}>{p.title} — v{p.version_no}</Link><Badge value={p.lifecycle} label={words(p.lifecycle)} /></div>
            <p className="small">{p.steps.length} role-owned steps · owner {p.owner_name}</p>
          </div>
        )) : <Empty>No SOP versions yet.</Empty>}
      </Card>
      <Card title="Owned knowledge work" testId="work-items">
        {work.data?.length ? work.data.map((w) => (
          <div className="item" key={w.id}><div className="row"><strong>{w.reason}</strong><Badge value="pending" label={words(w.work_kind)} /></div>
            <p className="small">Owner {w.owner_name} · next: {w.next_action}</p></div>
        )) : <Empty>No open review-due or dependent-review work.</Empty>}
      </Card>
    </>
  );
}
