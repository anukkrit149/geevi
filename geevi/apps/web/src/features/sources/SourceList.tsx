"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Loading, Select, TextInput } from "@/components/ui";
import { api, fileToBase64 } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { day } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

export const DOC_KINDS = [["referral", "Referral letter"], ["blood_panel", "Blood count panel"], ["marrow", "Bone marrow morphology"], ["flow", "Flow cytometry"],
  ["cytogenetics", "Cytogenetics"], ["molecular", "Molecular panel"], ["organ_assessment", "Organ assessment"], ["other", "Other (manual entry only)"]] as const;

export function SourceList({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const { can } = useWorkspace(workspaceId);
  const docs = useWs(workspaceId, ["patient", patientId, "sources"], () =>
    api.GET("/api/v1/workspaces/{workspace_id}/sources", { params: { path: { workspace_id: workspaceId }, query: { patient_id: patientId } } }));
  const action = useAction(workspaceId);
  const fileRef = useRef<HTMLInputElement>(null);
  const [kind, setKind] = useState("referral");
  const [issuer, setIssuer] = useState("");
  const [accession, setAccession] = useState("");
  const [relation, setRelation] = useState("");
  const [received, setReceived] = useState<string | null>(null);

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const content_base64 = await fileToBase64(file);
    const result = await action.run(`upload:${file.name}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/sources", {
      params: { path: { workspace_id: workspaceId } },
      body: { command_id, patient_id: patientId, filename: file.name, media_type: file.type || "application/octet-stream", content_base64, doc_kind: kind,
        issuer: issuer || null, accession: accession || null, relation: (relation || null) as never },
    }), `Received ${file.name}`);
    if (result) {
      setReceived(`${file.name}: ${String(result.data.association_status)} — ${String(result.data.candidate_count)} candidate finding(s) extracted.`);
      if (fileRef.current) fileRef.current.value = "";
      setIssuer("");
      setAccession("");
      setRelation("");
    }
  }

  return (
    <>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      <Card title="Source documents" testId="source-list">
        {docs.isLoading ? <Loading what="documents" /> : null}
        {docs.data?.length ? (
          <div className="table-wrap"><table>
            <thead><tr><th>Document</th><th>Issuer · accession</th><th>Received</th><th>Association</th><th>Original</th></tr></thead>
            <tbody>
              {docs.data.map((d) => (
                <tr key={d.id} data-testid={`doc-${d.filename}`}>
                  <td><Link href={`/w/${workspaceId}/patients/${patientId}/sources/${d.id}`}>{d.title}</Link><div className="small">{d.filename} · {d.doc_kind.replace("_", " ")}</div></td>
                  <td>{d.issuer ?? "—"}<div className="small">{d.external_id ?? "no accession"}</div></td>
                  <td>{day(d.received_time)}<div className="small">by {d.recorded_by_name}</div></td>
                  <td><Badge value={d.association_status} /></td>
                  <td>{d.original_available ? <span className="mono" title={d.sha256 ?? ""}>{d.sha256?.slice(0, 12)}…</span> : <Badge value="failed" label="unavailable" />}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        ) : docs.data ? <Empty>No documents received for this patient.</Empty> : null}
      </Card>
      {can("source.import") ? (
        <Card title="Receive a source document" testId="upload">
          <p className="small">The original bytes are stored unchanged with their SHA-256. PDF, PNG and JPEG only. A new document always starts unassociated.</p>
          <form onSubmit={(e) => { e.preventDefault(); void upload(); }}>
            <div className="grid grid-3">
              <div className="field"><label htmlFor="source-file">Original file</label><input id="source-file" ref={fileRef} type="file" accept="application/pdf,image/png,image/jpeg" required /></div>
              <Select label="Report type" value={kind} onChange={setKind} options={DOC_KINDS.map(([value, label]) => ({ value, label }))} />
              <Select label="Relation to an earlier report" value={relation} onChange={setRelation} hint="Leave as stated in the document unless you know otherwise."
                options={[{ value: "", label: "As stated in the document" }, { value: "original", label: "Original" }, { value: "additive_addendum", label: "Additive addendum" },
                  { value: "correction", label: "Correction" }, { value: "replacement", label: "Replacement" }, { value: "withdrawal", label: "Withdrawal" }]} />
              <TextInput label="Issuer (if not printed on the document)" value={issuer} onChange={setIssuer} />
              <TextInput label="Accession (if not printed on the document)" value={accession} onChange={setAccession} />
            </div>
            <Button variant="primary" type="submit" busy={!!action.pending}>Receive document</Button>
          </form>
          {received ? <p role="status" data-testid="upload-result">{received}</p> : null}
        </Card>
      ) : null}
    </>
  );
}
