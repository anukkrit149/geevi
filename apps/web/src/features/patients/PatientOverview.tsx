"use client";

import Link from "next/link";
import { Badge, Card, Loading } from "@/components/ui";
import { api } from "@/lib/api/client";
import { usePatient, useWs } from "@/lib/api/hooks";
import { day, valueWithUnits, words } from "@/lib/format";

/** Decision-oriented summary of server records; never derives a diagnosis, risk group or treatment. */
export function PatientOverview({ workspaceId, patientId }: { workspaceId: string; patientId: string }) {
  const base = `/w/${workspaceId}/patients/${patientId}`;
  const path = { workspace_id: workspaceId, patient_id: patientId };
  const patient = usePatient(workspaceId, patientId);
  const profile = useWs(workspaceId, ["patient", patientId, "profile", ""], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/profile", { params: { path } }));
  const plans = useWs(workspaceId, ["patient", patientId, "plans"], () => api.GET("/api/v1/workspaces/{workspace_id}/patients/{patient_id}/plans", { params: { path } }));
  const followups = useWs(workspaceId, ["patient", patientId, "follow-ups"], () => api.GET("/api/v1/workspaces/{workspace_id}/follow-ups", { params: { path: { workspace_id: workspaceId }, query: { patient_id: patientId } } }));
  const concerns = useWs(workspaceId, ["patient", patientId, "concerns"], () => api.GET("/api/v1/workspaces/{workspace_id}/concerns", { params: { path: { workspace_id: workspaceId }, query: { patient_id: patientId } } }));
  const questions = useWs(workspaceId, ["research", "questions"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/questions", { params: { path: { workspace_id: workspaceId } } }));
  if (profile.isLoading) return <Loading what="patient overview" />;
  if (!profile.data) return <div role="alert" className="card">Patient overview could not be loaded. Reload to review this patient.</div>;
  const p = profile.data;
  const current = plans.data?.find((v) => v.plan.status === "approved");
  const pending = plans.data?.find((v) => ["draft", "submitted"].includes(v.plan.status));
  const openFollowups = followups.data?.filter((o) => !["fulfilled", "cancelled"].includes(o.state)) ?? [];
  const openConcerns = concerns.data?.filter((c) => c.status !== "closed") ?? [];
  const linkedQuestions = questions.data?.filter((q) => (q.origin as { patient_id?: string } | null)?.patient_id === patientId) ?? [];
  const observations = p.dimensions.flatMap((d) => d.observations);
  const course = observations.filter((o) => ["Treatment received", "Treatment period", "Treatment intent", "Treatment complications", "Treatment modification", "Reported response", "Response assessment date"].includes(o.analyte));
  const burden = observations.filter((o) => ["Reported diagnosis", "Blast percentage", "Measurable residual disease", "Extramedullary assessment"].includes(o.analyte));
  const awaited = p.unresolved.filter((u) => u.kind === "expected_input");
  const unavailable = observations.filter((o) => o.dimension === "biology" && ["pending", "indeterminate", "insufficient_sample", "untested", "unreported", "unavailable"].includes(o.result_state));
  const finding = (o: typeof observations[number]) => <p className="small" key={o.id}><strong>{o.analyte}:</strong> {valueWithUnits(o.value_text, o.units)}<br /><span>{day(o.effective_time)} · <Link href={`${base}/sources/${o.document_id}?observation=${o.id}`}>Source report</Link></span></p>;
  return (
    <>
    <div className="grid grid-2">
      <Card title="Disease and recorded burden" testId="disease-burden">{burden.length ? burden.map(finding) : <p>No source-verified disease assessment yet. Review the received reports before recording the clinical interpretation.</p>}<p className="small">The assessment uses disease-specific findings. An AML stage or remission category is not inferred from these values.</p></Card>
      <Card title="Treatment received and recorded outcomes" testId="treatment-outcomes">{course.length ? course.map(finding) : <p>No source-verified treatment course or response assessment recorded. A proposed plan does not establish that treatment was given.</p>}<p className="small">Reported complications, response measurements and formal clinician interpretation are kept distinct.</p></Card>
    </div>
    <Card title="Clinical overview" testId="patient-overview">
      <p>{patient.data?.patient.summary || "No referral summary recorded."}</p>
      <div className="grid grid-2">
        <div><h3>Clinical assessment</h3><p>{p.assessment?.narrative || "Awaiting the oncologist’s assessment. Source findings below remain separate from clinical interpretation."}</p>
          {p.assessment?.uncertainty ? <p className="small"><strong>Uncertainty:</strong> {p.assessment.uncertainty}</p> : null}
          <h3>Patient goals</h3><p>{p.discussion?.goals || "Not documented — discuss goals, preferences and practical constraints before approving a plan."}</p>
        </div>
        <div><h3>Current decision</h3>
          {plans.isLoading ? <p>Loading plan…</p> : plans.error ? <p role="alert">Plan status unavailable. Open Plan & decisions to retry.</p> : current ? <><p>{current.plan.intent}</p><Badge value={current.currency.status} /><p className="small">Signed plan v{current.plan.version_no} · {words(current.disposition ?? "active")}</p><Link href={`/w/${workspaceId}/department/protocols/${current.plan.protocol_version_id}`}>Shared protocol used by this plan</Link></> : <p>No signed plan yet. Review the case, discuss goals, assess a published protocol and document the individual decision.</p>}
          {pending ? <p className="small">Plan v{pending.plan.version_no} is {words(pending.plan.status)}.</p> : null}
          <p><Link href={`${base}/decisions`}>Review applicability, exceptions and plan</Link></p>
        </div>
      </div>
      <div className="grid grid-3">
        <div><h3>Investigations and information awaited</h3>{awaited.map((u, i) => <p className="small" key={i}>{u.text}</p>)}{unavailable.slice(0, 3).map((o) => <p className="small" key={o.id}>{o.analyte}: {o.value_text || words(o.result_state)}</p>)}{!awaited.length && !unavailable.length ? <p className="small">No pending investigation recorded. This does not establish that the workup is complete.</p> : null}<Link href={`${base}/sources`}>Review reports and missing information</Link></div>
        <div><h3>Follow-up</h3>{followups.error ? <p role="alert">Follow-up status unavailable.</p> : openFollowups.length ? openFollowups.map((o) => <p className="small" key={o.id}>{o.purpose} · {day(o.due)} · {o.owner_name} <Badge value={o.state} /></p>) : <p className="small">No open follow-up obligation recorded.</p>}<Link href={`${base}/care`}>Open care, concerns and follow-up</Link>{openConcerns.length ? <p className="small">{openConcerns.length} open concern(s) require a response or review.</p> : null}</div>
        <div><h3>Research for this case</h3><p className="small">Related areas: AML classification and molecular risk; treatment outcomes and harms; response and MRD; genomic and assay research. Start from the uncertainty in this case.</p><Link href={`/w/${workspaceId}/research?patient=${patientId}`}>Review evidence or ask a case-linked question</Link>{linkedQuestions.map((q) => <p className="small" key={q.id}><Link href={`/w/${workspaceId}/research/${q.id}`}>{q.title}</Link> · {q.conclusion ? words(q.conclusion) : "open"}</p>)}<p className="small">The research library shows study populations, outcomes, limitations and review depth. Published trial outcomes are separate from this patient’s recorded response.</p></div>
      </div>
      <details><summary>How this patient journey works</summary><ol><li>Coordinator verifies identity and source findings; the oncologist records assessment and patient goals.</li><li>The research lead appraises published evidence; an independent reviewer approves or objects.</li><li>The lead authors and publishes the shared protocol and SOP after review.</li><li>The treating oncologist assesses applicability, records any exception, and signs the patient’s individual plan.</li><li>The care team accepts tasks and records actual care; follow-up and concerns return to a named owner.</li><li>New reports or protocol changes trigger a review of affected patients.</li></ol></details>
    </Card>
</>
  );
}
