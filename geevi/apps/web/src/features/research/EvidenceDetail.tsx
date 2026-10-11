"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge, Button, Card, ErrorSummary, Loading, TextArea, TextInput } from "@/components/ui";
import { SourceViewer } from "@/features/sources/SourceViewer";
import { api, fileToBase64 } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { useWorkspace } from "@/lib/session/session";

export function citationUrl(citation: string): string | null {
  const match = citation.match(/https?:\/\/[^\s<>]+/);
  return match ? match[0].replace(/[.,;)]$/, "") : null;
}

export function EvidenceDetail({ workspaceId, sourceId }: { workspaceId: string; sourceId: string }) {
  const path = { workspace_id: workspaceId, source_id: sourceId };
  const { can } = useWorkspace(workspaceId);
  const source = useWs(workspaceId, ["research", "source", sourceId], () => api.GET("/api/v1/workspaces/{workspace_id}/research/sources/{source_id}", { params: { path } }));
  const action = useAction(workspaceId);
  const [reason, setReason] = useState("");
  const [amendment, setAmendment] = useState({ title: "", citation: "", reason: "" });
  const file = useRef<HTMLInputElement>(null);
  const router = useRouter();
  if (source.isLoading) return <Loading what="evidence document" />;
  if (!source.data) return <div className="card" role="alert">Evidence document unavailable in this workspace.</div>;
  const s = source.data;
  const url = citationUrl(s.citation);
  return <>
    <div className="page-head"><div><h1>{s.title}</h1><p>{s.citation}</p></div><Badge value={s.status} /></div>
    <p><Link href={`/w/${workspaceId}/research`}>Back to research library</Link>{url ? <> · <a href={url} target="_blank" rel="noreferrer">Open original publication</a></> : null}</p>
    <p className="small">Evidence source v{s.version_no} · {s.source_label === "public_reference" ? "Published reference" : "Synthetic teaching material"}. Geevi evidence briefs are attributed summaries; consult the linked publication for full methods, tables and updates.</p>
    {s.file_available ? <SourceViewer contentPath={`/api/v1/workspaces/${workspaceId}/research/sources/${sourceId}/content`} mediaType="application/pdf" available highlight={null} /> : <Card title="Citation only"><p>No document is held for this citation.</p></Card>}
    <Card title="Citable passages" testId="evidence-passages"><p className="small">Use these passages in an appraisal, and record both findings and limitations.</p>{(s.passages as { id: string; text: string; page: number }[]).map((p) => <p className="quote" key={p.id}>{p.text} <span className="small">(page {p.page})</span></p>)}</Card>
    {can("evidence.author") && s.status === "active" ? <Card title="Amend an evidence source"><details><summary>Create a corrected source version</summary><form onSubmit={async (e) => { e.preventDefault(); const f = file.current?.files?.[0]; const content_base64 = f ? await fileToBase64(f) : null; const done = await action.run("amend", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/sources/{source_id}/amend", { params: { path }, body: { command_id, expected_revision: s.revision, reason: amendment.reason, title: amendment.title || null, citation: amendment.citation || null, media_type: f ? "application/pdf" : null, content_base64 } }), "Corrected evidence version created; dependent appraisals require review"); if (done?.target) router.push(`/w/${workspaceId}/research/sources/${done.target.id}`); }}><ErrorSummary error={action.error} /><TextInput label="Corrected source title (optional)" value={amendment.title} onChange={(title) => setAmendment({ ...amendment, title })} /><TextArea label="Corrected citation (optional)" value={amendment.citation} onChange={(citation) => setAmendment({ ...amendment, citation })} /><TextArea label="Amendment reason" value={amendment.reason} onChange={(reason) => setAmendment({ ...amendment, reason })} required minLength={8} /><label htmlFor="corrected-evidence">Replacement evidence PDF (optional)</label><input id="corrected-evidence" ref={file} type="file" accept="application/pdf" /><Button type="submit">Create corrected source version</Button><p className="small">The previous document stays in history. Dependent appraisals and protocols are flagged for review.</p></form></details></Card> : null}
    {can("evidence.author") && s.status === "active" ? <Card title="Withdraw an evidence source"><ErrorSummary error={action.error} /><TextArea label="Withdrawal reason" value={reason} onChange={setReason} /><Button variant="danger" disabled={reason.trim().length < 8} onClick={() => action.run("withdraw", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/sources/{source_id}/withdraw", { params: { path }, body: { command_id, expected_revision: s.revision, reason } }), "Evidence source withdrawn; affected decisions require review")}>Withdraw source</Button></Card> : null}
  </>;
}
