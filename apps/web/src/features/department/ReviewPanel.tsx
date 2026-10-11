"use client";

import { useState } from "react";
import { Badge, Button, Empty, ErrorSummary, TextArea } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useAction } from "@/lib/api/useAction";
import { when } from "@/lib/format";
import { useSession } from "@/lib/session/session";

type PacketView = Schemas["PacketView"];

/** Independent review history and, for the assigned reviewer only, the decision form. */
export function ReviewPanel({ workspaceId, reviews }: { workspaceId: string; reviews: PacketView[] }) {
  const { session } = useSession();
  const action = useAction(workspaceId);
  const [rationale, setRationale] = useState("");
  if (!reviews.length) return <Empty>Not yet submitted for independent review.</Empty>;
  return (
    <div data-testid="review-panel">
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {reviews.map(({ packet, assignments, decisions }) => {
        const mine = assignments.some((a) => a.assignee_id === session?.account.id);
        const decide = (decision: "approve" | "object") => action.run(`decide:${packet.id}`, (command_id) =>
          api.POST("/api/v1/workspaces/{workspace_id}/review-packets/{packet_id}/decide", { params: { path: { workspace_id: workspaceId, packet_id: packet.id } },
            body: { command_id, expected_revision: packet.revision, decision, rationale: rationale || null } }),
          decision === "approve" ? "Approval recorded" : "Objection recorded").then((done) => { if (done) setRationale(""); });
        return (
          <div className="item" key={packet.id}>
            <div className="row"><strong>Review packet</strong><Badge value={packet.status} />
              <span className="small">author {packet.author_name} · reviewer {assignments.map((a) => a.assignee_name).join(", ")} · policy v{String((packet.policy as Record<string, any>).version ?? "—")}</span></div>
            <p className="small mono">frozen digest {packet.target_digest}</p>
            {decisions.map((d) => (
              <p className="quote" key={d.id} data-testid={`decision-${d.decision}`}>{d.decision === "approve" ? "Approved" : "Objection"} by {d.recorded_by_name} · {when(d.recorded_at)}{d.rationale ? ` — ${d.rationale}` : ""}</p>
            ))}
            {packet.status === "open" && mine ? (
              <fieldset data-testid="review-decision">
                <legend>Your independent review decision</legend>
                <TextArea label="Rationale (required for an objection)" value={rationale} onChange={setRationale} rows={2} />
                <div className="row">
                  <Button variant="primary" busy={action.pending === `decide:${packet.id}`} onClick={() => void decide("approve")}>Approve</Button>
                  <Button variant="danger" onClick={() => void decide("object")}>Object</Button>
                </div>
              </fieldset>
            ) : null}
            {packet.status === "open" && !mine ? <p className="small">Awaiting the assigned reviewer. The author cannot review their own version.</p> : null}
            {packet.status === "changes_requested" ? <p className="small">An objection is unresolved: the author must submit a successor revision.</p> : null}
          </div>
        );
      })}
    </div>
  );
}
