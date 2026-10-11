"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, ErrorSummary, Select, TextInput } from "@/components/ui";
import { api } from "@/lib/api/client";
import { useMembers } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { useSession, useWorkspace } from "@/lib/session/session";

type Version = { id: string; revision: number; status: string; lifecycle: string; recorded_by?: string | null; version_no: number };

/** Submit → (independent approval) → publish → withdraw / revise. Shared by protocol and SOP versions. */
export function PublicationBar({ workspaceId, kind, version, evidence, onBeforeSubmit }: {
  workspaceId: string; kind: "protocols" | "sops"; version: Version; evidence?: string[]; onBeforeSubmit?: () => Promise<number | null>;
}) {
  const { can } = useWorkspace(workspaceId);
  const { session } = useSession();
  const router = useRouter();
  const members = useMembers(workspaceId);
  const action = useAction(workspaceId);
  const noun = kind === "protocols" ? "protocol" : "sop";
  const reviewers = (members.data ?? []).filter((m) => m.capabilities.includes(`${noun}.review`));
  const [reviewer, setReviewer] = useState("");
  const [reason, setReason] = useState("");
  const [effective, setEffective] = useState("");
  const params = { path: { workspace_id: workspaceId, version_id: version.id } };
  const author = version.recorded_by === session?.account.id;
  const chosen = reviewer || reviewers[0]?.username || "";

  return (
    <div data-testid="publication-bar">
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {version.status === "draft" && author && can(`${noun}.author`) ? (
        <div className="row" style={{ alignItems: "flex-end" }}>
          <Select label="Independent reviewer" value={chosen} onChange={setReviewer}
            options={reviewers.length ? reviewers.map((m) => ({ value: m.username, label: `${m.display_name} — ${m.role_title}` })) : [{ value: "", label: "No account holds the review grant" }]} />
          <Button variant="primary" style={{ marginBottom: ".6rem" }} busy={action.pending === "submit"} onClick={async () => {
            const revision = onBeforeSubmit ? await onBeforeSubmit() : version.revision;
            if (revision === null) return;
            await action.run("submit", (command_id) => api.POST(`/api/v1/workspaces/{workspace_id}/${kind}/{version_id}/submit`, {
              params, body: { command_id, expected_revision: revision, reviewer_username: chosen || null } }), "Frozen and submitted for independent review");
          }}>Save and submit for independent review</Button>
        </div>
      ) : null}
      {version.status === "approved" && can(`${noun}.publish`) ? (
        <div className="row" style={{ alignItems: "flex-end" }}>
          <TextInput label="Effective from (optional; default now)" type="datetime-local" value={effective} onChange={setEffective} />
          <Button variant="primary" style={{ marginBottom: ".6rem" }} busy={action.pending === "publish"} onClick={() => action.run("publish", (command_id) =>
            api.POST(`/api/v1/workspaces/{workspace_id}/${kind}/{version_id}/publish`, { params, body: { command_id, expected_revision: version.revision,
              effective_from: effective ? new Date(effective).toISOString() : null } }), `Version ${version.version_no} published`)}>
            Publish version {version.version_no}
          </Button>
        </div>
      ) : null}
      {version.status === "approved" && !can(`${noun}.publish`) ? <p className="small">Approved. Awaiting the publisher&apos;s separate publication decision.</p> : null}
      {["published", "withdrawn", "changes_requested"].includes(version.status) && can(`${noun}.author`) ? (
        <fieldset>
          <legend>{version.status === "published" ? "Propose a change or withdraw" : "Propose a successor revision"}</legend>
          <TextInput label="Rationale / reason" value={reason} onChange={setReason} />
          <div className="row">
            <Button busy={action.pending === "revise"} onClick={async () => {
              const done = await action.run("revise", (command_id) => api.POST(`/api/v1/workspaces/{workspace_id}/${kind}/{version_id}/revise`, {
                params, body: { command_id, rationale: reason, evidence: evidence ?? [] } }), "Change proposal opened with a successor draft");
              if (done?.target) { setReason(""); router.push(`/w/${workspaceId}/department/${kind}/${done.target.id}`); }
            }}>Open change proposal (successor draft)</Button>
            {version.status === "published" && can(`${noun}.publish`) ? (
              <Button variant="danger" onClick={() => action.run("withdraw", (command_id) => api.POST(`/api/v1/workspaces/{workspace_id}/${kind}/{version_id}/withdraw`, {
                params, body: { command_id, expected_revision: version.revision, reason } }), "Version withdrawn; dependant review nominated")}>Withdraw this version</Button>
            ) : null}
          </div>
        </fieldset>
      ) : null}
    </div>
  );
}
