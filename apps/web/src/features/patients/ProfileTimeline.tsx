"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Loading, Select, TextArea, TextInput } from "@/components/ui";
import { api } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { day, valueWithUnits, when, words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

/** Six-dimensional longitudinal profile: a projection over source records at a knowledge cutoff. */
export function ProfileTimeline({ workspaceId, patientId, recordHistory = false }: { workspaceId: string; patientId: string; recordHistory?: boolean }) {
  const { can } = useWorkspace(workspaceId);
  const path = { workspace_id: workspaceId, patient_id: patientId };
  const [cutoff, setCutoff] = useState("");
  const profile = useWs(workspaceId, ["patient", patientId, "profile", cutoff], () =>
    api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/profile", { params: { path, query: cutoff ? { as_of_seq: Number(cutoff) } : {} } }));
  const snapshots = useWs(workspaceId, ["patient", patientId, "snapshots"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/snapshots", { params: { path } }));
  const timeline = useWs(workspaceId, ["patient", patientId, "timeline"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/timeline", { params: { path } }));
  const legacy = useWs(workspaceId, ["patient", patientId, "legacy"], () => api.GET("/api/v1/workspaces/{workspace_id}/legacy-records", { params: { path: { workspace_id: workspaceId }, query: { patient_id: patientId } } }));
  const action = useAction(workspaceId);
  const [assessment, setAssessment] = useState({ narrative: "", uncertainty: "", fitness: "" });
  const [dimensionNotes, setDimensionNotes] = useState<Record<string, string>>({});

  if (profile.isLoading) return <Loading what="profile" />;
  const p = profile.data;
  if (!p) return null;
  const sourceHref = (o: { document_id: string; id: string }) => `/w/${workspaceId}/patients/${patientId}/sources/${o.document_id}?observation=${o.id}`;

  return (
    <>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {recordHistory ? <Card title="Record history" testId="cutoff">
        <div className="row">
          <div style={{ minWidth: 320 }}>
            <Select label="Show the profile as it was known at" value={cutoff} onChange={setCutoff}
              options={[{ value: "", label: "Now (current knowledge)" }, ...(snapshots.data ?? []).map((s) => ({ value: String(s.knowledge_cutoff_seq), label: `Snapshot at sequence ${s.knowledge_cutoff_seq} (${when(s.recorded_at)})` }))]} />
          </div>
          {p.historical ? <Badge value="held" label="Historical view" /> : <Badge value="current" label="Latest record" />}
        </div>
        <p className="small">Review the information available at an earlier decision. Reports received later appear only in subsequent versions.</p>
      </Card> : null}

      <div className="grid grid-2" data-testid="dimensions">
        {p.dimensions.filter((d) => recordHistory || d.clinician_note || d.observations.length).map((d) => (
          <section className="card dimension" key={d.id} aria-label={d.title} data-testid={`dimension-${d.id}`}>
            <h3><span>{d.title}</span></h3>
            <p className="small">{d.description}</p>
            {d.clinician_note ? <p className="quote">{d.clinician_note}</p> : null}
            {d.observations.length ? <details open={recordHistory || !d.clinician_note}><summary>Reported findings ({d.observations.length})</summary>{d.observations.map((o) => (
              <div className="item" key={o.id}>
                <div className="row">
                  <strong>{o.analyte}</strong><span>{valueWithUnits(o.value_text, o.units)} {o.reference_range ? <span className="small">(ref {o.reference_range})</span> : null}</span>
                  {o.result_state !== "reported_value" ? <Badge value={["detected", "not_detected"].includes(o.result_state) ? "reviewed" : "pending"} label={o.result_state === "unreported" ? "not reported" : o.result_state === "untested" ? "not tested" : o.result_state === "pending" ? "result pending" : words(o.result_state)} /> : null}
                </div>
                <p className="small">{o.specimen_label ? `${o.specimen_label} · ` : ""}{day(o.effective_time)} · <Link href={sourceHref(o)}>Open source region</Link></p>
              </div>
            ))}</details> : !d.clinician_note ? <p className="small">Not documented yet. Missing information is not assumed normal.</p> : null}
            {recordHistory ? d.unresolved.map((u) => <p className="small" key={u}>{u}</p>) : null}
          </section>
        ))}
      </div>

      {p.trends.length ? (
        <Card title="Results over time" testId="trends">
          <div className="table-wrap"><table>
            <thead><tr><th>Finding</th><th>Values by clinical time</th></tr></thead>
            <tbody>{p.trends.map((t) => (
              <tr key={t.analyte}><td>{t.analyte}</td><td>{t.points.map((pt) => `${day(pt.effective_time)}${pt.specimen_label ? ` (${pt.specimen_label})` : ""}: ${pt.value_text ? valueWithUnits(pt.value_text, pt.units) : words(pt.result_state)}`).join("  →  ")}</td></tr>
            ))}</tbody>
          </table></div>
        </Card>
      ) : null}

      {recordHistory ? <div className="grid grid-2">
        <Card title={`Information awaiting review (${p.unresolved.length})`} testId="unresolved">
          {p.unresolved.length ? p.unresolved.map((u, i) => (
            <div className="item" key={i}>
              <span>{u.text}</span>
              <p className="small">{u.owner ? `Owner: ${u.owner} · ` : ""}{u.next_action ? `Next: ${u.next_action}` : ""}
                {u.target_kind === "source_document" ? <> · <Link href={`/w/${workspaceId}/patients/${patientId}/sources/${u.target_id}`}>Open document</Link></> : null}</p>
            </div>
          )) : <Empty>Nothing unresolved at this cutoff.</Empty>}
        </Card>


      </div> : null}

      <div className="grid grid-2">
        <Card title="Clinical assessment" testId="assessment">
          {p.assessment ? (
            <>
              <p className="quote">{p.assessment.narrative}</p>
              <p className="small">Version {p.assessment.version_no} · {p.assessment.recorded_by_name} · {when(p.assessment.recorded_at)}{p.assessment.uncertainty ? ` · Uncertainty: ${p.assessment.uncertainty}` : ""}</p>
            </>
          ) : <Empty>No clinician assessment recorded at this cutoff.</Empty>}
          {can("clinical.assess") && !recordHistory ? <details><summary>Update clinical assessment</summary>
            <form onSubmit={async (e) => {
              e.preventDefault();
              const done = await action.run("assessment", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/assessments", {
                params: { path }, body: { command_id, narrative: assessment.narrative, uncertainty: assessment.uncertainty || null, dimension_notes: { ...Object.fromEntries(Object.entries(dimensionNotes).filter(([, v]) => v.trim())), ...(assessment.fitness ? { fitness: assessment.fitness } : {}) } } }), "Assessment recorded");
              if (done) { setAssessment({ narrative: "", uncertainty: "", fitness: "" }); setDimensionNotes({}); }
            }}>
              <TextArea label="Assessment narrative" value={assessment.narrative} onChange={(narrative) => setAssessment({ ...assessment, narrative })} required
                hint="Clinician interpretation, kept separate from laboratory observations and from source review." />
              <TextInput label="Fitness note (optional)" value={assessment.fitness} onChange={(fitness) => setAssessment({ ...assessment, fitness })} />
              <details><summary>Assessment by clinical dimension (optional)</summary>{p.dimensions.filter((d) => d.id !== "fitness").map((d) => <TextArea key={d.id} label={`${d.title} — clinician interpretation`} value={dimensionNotes[d.id] ?? ""} onChange={(v) => setDimensionNotes({ ...dimensionNotes, [d.id]: v })} rows={2} />)}</details>
              <TextInput label="Stated uncertainty (optional)" value={assessment.uncertainty} onChange={(uncertainty) => setAssessment({ ...assessment, uncertainty })} />
              <Button type="submit" busy={action.pending === "assessment"}>Record assessment</Button>
            </form>
          </details> : null}
        </Card>
        <Card title="Patient discussion" testId="discussion-summary">
          {p.discussion ? (
            <>
              <p className="quote">{p.discussion.goals}</p>
              <p className="small">Attributed to the {p.discussion.attributed_to}; entered by {p.discussion.recorded_by_name} · version {p.discussion.version_no}</p>
              {p.discussion.preferences ? <p className="small">Preferences: {p.discussion.preferences}</p> : null}
            </>
          ) : <Empty>No discussion documented yet. Record it under Decisions.</Empty>}
        </Card>
      </div>

      {legacy.data?.length ? (
        <Card title={`Legacy history (${legacy.data.length} unmapped records)`} testId="legacy-records" tone="warn">
          <p className="small">Imported from the legacy prototype and preserved verbatim. These are not reviewed publications and not signatures in this application.</p>
          {legacy.data.map((record) => (
            <details key={record.id} className="item">
              <summary><strong>{words(record.legacy_kind)}</strong> <Badge value="superseded" label={record.mapping_status} /> <span className="small">{record.note}</span></summary>
              <pre className="quote mono">{JSON.stringify(record.payload, null, 2)}</pre>
            </details>
          ))}
        </Card>
      ) : null}

      <details open={recordHistory}><summary>Clinical and care timeline</summary><Card title="Timeline" testId="timeline">
        {timeline.data?.length ? (
          <ol className="timeline">
            {timeline.data.map((row, i) => (
              <li key={`${row.target_id}-${i}`} data-lane={row.lane}>
                <div><span className="lane">{row.lane}</span><div className="small">{row.clinical_time ? day(row.clinical_time) : `seq ${row.seq}`}</div></div>
                <div><strong>{row.title}</strong>{row.detail ? <p className="small">{row.detail}</p> : null}<p className="small">{row.actor} · recorded {when(row.recorded_at)}</p></div>
              </li>
            ))}
          </ol>
        ) : <Empty>No events recorded yet.</Empty>}
      </Card></details>
    </>
  );
}
