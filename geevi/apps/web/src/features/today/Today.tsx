"use client";

import Link from "next/link";
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
    case "expected_input": return `${base}/patients/${entry.patient_id}`;
    case "exception_request":
    case "patient_plan_version": return `${base}/patients/${entry.patient_id}/decisions`;
    case "task":
    case "follow_up_obligation":
    case "concern": return `${base}/patients/${entry.patient_id}/care`;
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

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Today</h1>
          <p>Owned work for {session?.account.display_name}. Each item names its next action.</p>
        </div>
      </div>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {today.isLoading ? <Loading what="your work" /> : null}
      {today.data && !today.data.items.length ? <Card title="Nothing is waiting on you"><Empty>No owned work for this account right now.</Empty></Card> : null}
      <div data-testid="worklist">
        {GROUPS.map(([kind, title]) => {
          const items = today.data?.items.filter((i) => i.kind === kind) ?? [];
          if (!items.length) return null;
          return (
            <Card key={kind} title={`${title} (${items.length})`} testId={`work-${kind}`}>
              {items.map((item, index) => (
                <div className="item" key={`${item.target_id}-${index}`}>
                  <div className="row">
                    <Link className="item-title" href={hrefFor(workspaceId, item)}>{item.title}</Link>
                    <Badge value={item.state} />
                  </div>
                  <p className="small">{item.detail}{item.owner ? ` · Owner: ${item.owner}` : ""}</p>
                  {item.next_action ? <p className="small"><strong>Next:</strong> {item.next_action}</p> : null}
                </div>
              ))}
            </Card>
          );
        })}
      </div>
      <Card title="Team notes (non-clinical)" testId="notes">
        {notes.data?.length ? notes.data.map((n) => (
          <div className="item" key={n.id}>
            <span>{n.text}</span> <span className="small">— {n.recorded_by_name}</span> <Badge value={n.status} />
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
    </>
  );
}
