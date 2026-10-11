"use client";

import Link from "next/link";
import { ArrowUpRight, CheckCircle, ClipboardText, ArrowRight, Users, BookOpen } from "@phosphor-icons/react";
import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Loading, TextInput } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { useSession, useWorkspace } from "@/lib/session/session";

type Entry = Schemas["WorkEntry"];

export function hrefFor(ws: string, entry: Pick<Entry, "kind" | "patient_id" | "target_kind" | "target_id">): string {
  const base = `/w/${ws}`;
  switch (entry.target_kind) {
    case "protocol_version": return `${base}/department/protocols/${entry.target_id}`;
    case "sop_version": return `${base}/department/sops/${entry.target_id}`;
    case "research_question": return `${base}/research/${entry.target_id}`;
    case "impact_review": return `${base}/impacts`;
    case "source_document": return entry.patient_id ? `${base}/patients/${entry.patient_id}/sources/${entry.target_id}` : `${base}/patients`;
    case "expected_input": return `${base}/patients/${entry.patient_id}/sources#readiness`;
    case "exception_request": return `${base}/patients/${entry.patient_id}/decisions#exceptions`;
    case "patient_plan_version": return `${base}/patients/${entry.patient_id}/decisions#plan`;
    case "task": return `${base}/patients/${entry.patient_id}/care#tasks`;
    case "follow_up_obligation": return `${base}/patients/${entry.patient_id}/care#follow-ups`;
    case "concern": return `${base}/patients/${entry.patient_id}/care#concerns`;
    default: return `${base}/today`;
  }
}

const GROUPS: [string, string][] = [["review", "Independent reviews"], ["exception", "Exception decisions"], ["plan", "Plans awaiting your action"],
  ["impact", "Impact reviews you own"], ["source", "Source intake and verification"], ["task", "Handoff tasks"], ["follow_up", "Follow-up duties"],
  ["concern", "Concerns"], ["expected_input", "Expected inputs"], ["work", "Knowledge work"]];

export function Today({ workspaceId }: { workspaceId: string }) {
  const { session } = useSession();
  const { can } = useWorkspace(workspaceId);
  const today = useWs(workspaceId, ["today"], () => api.GET("/api/v1/workspaces/{workspace_id}/today", { params: { path: { workspace_id: workspaceId } } }));
  const notes = useWs(workspaceId, ["notes"], () => api.GET("/api/v1/workspaces/{workspace_id}/notes", { params: { path: { workspace_id: workspaceId } } }));
  const action = useAction(workspaceId);
  const [note, setNote] = useState("");
  const [filter, setFilter] = useState("all");
  const items = today.data?.items ?? [];
  const groups = GROUPS.filter(([kind]) => items.some((i) => i.kind === kind));
  const activeFilter = filter === "all" || groups.some(([kind]) => kind === filter) ? filter : "all";
  const patients = new Set(items.map((i) => i.patient_id).filter(Boolean)).size;

  return (
    <>
      <div className="page-head"><div><span className="page-kicker">Your workspace, {session?.account.display_name}</span><h1>Today</h1><p>A clear place to start. Your work, grouped by the next action.</p></div>{can("records.read") ? <Link className="button-link" href={`/w/${workspaceId}/patients`}><Users aria-hidden="true" />View patients</Link> : null}</div>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {today.error ? <div className="error-summary" role="alert"><h2>Your work could not be loaded</h2><p>Refresh the worklist to see your current responsibilities.</p><Button onClick={() => today.refetch()}>Try again</Button></div> : null}
      {today.isLoading ? <Loading what="your work" /> : today.data ? <section className="today-summary" aria-label="Work overview">
        <div className="today-summary-copy"><h2>{items.length ? "Let’s move the next step forward." : "You’re up to date."}</h2><p>{items.length ? "Review what needs your attention, then return to the patient or shared record." : "There’s no owned work waiting for this account. Explore the patient workspace to continue."}</p>{items[0] ? <Link className="button-link button-link-primary" href={hrefFor(workspaceId, items[0])}>Open first item<ArrowRight aria-hidden="true" /></Link> : <CheckCircle aria-hidden="true" size={28} />}</div>
        <div className="today-summary-stats"><div><span className="stat-number">{items.length}</span><span className="stat-label">Owned items</span></div><div><span className="stat-number">{patients}</span><span className="stat-label">Linked patients</span></div></div>
      </section> : null}
      <div className="work-layout"><div>
        {groups.length > 1 ? <div className="filter-row" role="group" aria-label="Filter work"><button className="filter-chip" aria-pressed={activeFilter === "all"} onClick={() => setFilter("all")}>All work<span className="count">{items.length}</span></button>{groups.map(([kind, title]) => <button className="filter-chip" key={kind} aria-pressed={activeFilter === kind} onClick={() => setFilter(kind)}>{title}<span className="count">{items.filter((i) => i.kind === kind).length}</span></button>)}</div> : null}
        <div data-testid="worklist" className="view-enter" key={activeFilter}>
          {GROUPS.map(([kind, title]) => {
            const entries = items.filter((i) => i.kind === kind);
            if (!entries.length || (activeFilter !== "all" && activeFilter !== kind)) return null;
            return <Card key={kind} title={`${title} (${entries.length})`} testId={`work-${kind}`}>
              {entries.map((item, index) => <div className="item work-item" key={`${item.target_id}-${index}`}>
                <span className="work-item-icon"><ClipboardText aria-hidden="true" /></span>
                <div><div className="row"><Link className="item-title" href={hrefFor(workspaceId, item)}>{item.title}</Link><Badge value={item.state} /></div>
                {item.next_action ? <p className="next-action"><strong>Next:</strong> {item.next_action}</p> : null}
                <details><summary>Context{item.owner ? ` and owner` : ""}</summary><p className="small">{item.detail}{item.owner ? ` · Owner: ${item.owner}` : ""}</p></details></div>
                <Link className="icon-button" aria-label={`Open ${item.title}`} href={hrefFor(workspaceId, item)}><ArrowUpRight aria-hidden="true" /></Link>
              </div>)}
            </Card>;
          })}
        </div>
        {today.data && !items.length ? <Card title="Nothing is waiting on you"><div className="empty-state"><CheckCircle aria-hidden="true" /><Empty>No owned work for this account right now.</Empty><Link href={`/w/${workspaceId}/patients`}>Open patients</Link></div></Card> : null}
      </div><aside className="work-aside">
      <Card title="Team notes (non-clinical)" testId="notes">
        {notes.isLoading ? <p className="small" role="status">Loading team notes…</p> : notes.error ? <p className="small" role="alert">Team notes could not be loaded. <Button onClick={() => notes.refetch()}>Try again</Button></p> : notes.data?.length ? notes.data.map((n) => (
          <div className="item" key={n.id}>
            <span>{n.text}</span> <span className="small">by {n.recorded_by_name}</span> <Badge value={n.status} />
          </div>
        )) : <Empty>No notes yet.</Empty>}
        {can("note.write") ? (
          <form onSubmit={async (e) => {
            e.preventDefault();
            const done = await action.run("note", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/notes", { params: { path: { workspace_id: workspaceId } }, body: { command_id, text: note } }), "Note added");
            if (done) setNote("");
          }}>
            <TextInput label="Add a team note" value={note} onChange={setNote} hint="Operational reminders only. Not part of any clinical record." />
            <Button type="submit" busy={action.pending === "note"} disabled={!note.trim()}>Add note</Button>
          </form>
        ) : null}
      </Card>

      {can("records.read") ? <details className="card" data-testid="demo-orientation"><summary><BookOpen aria-hidden="true" size={18} /> Walk through the oncology department workflow</summary><p className="small">Start with a <Link href={`/w/${workspaceId}/patients`}>patient</Link>: understand disease findings, treatment received, recorded response and the current decision. Use <Link href={`/w/${workspaceId}/research`}>Research</Link> to examine evidence, its limits and applicability before proposing a <Link href={`/w/${workspaceId}/department`}>shared protocol</Link>.</p><p className="small">Demo roles: Rao authors research and patient plans; Sen reviews independently; Mira verifies reports and coordinates follow-up; Isha accepts handoffs and records care. These development accounts simulate the role split; approvals are not institutional signatures.</p></details> : null}
      </aside></div>
    </>
  );
}
