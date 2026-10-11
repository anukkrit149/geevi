"use client";

import Link from "next/link";
import { Badge, Card, Loading, Disclosure } from "@/components/ui";
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
  const finding = (o: typeof observations[number]) => <div className="overview-finding" key={o.id}><span className="finding-label">{o.analyte}</span><div className="finding-value">{valueWithUnits(o.value_text, o.units)}</div><div className="finding-source"><time>{day(o.effective_time)}</time><Link href={`${base}/sources/${o.document_id}?observation=${o.id}`}>Source report</Link></div></div>;
  return (
    <>
      <Card title="Clinical overview" testId="patient-overview">
        <div className="overview-lead">
          <div><p>{patient.data?.patient.summary || "No referral summary recorded."}</p>
            <Disclosure title="Recorded clinical assessment"><p className="small">{p.assessment?.narrative || "Awaiting the oncologist’s assessment. Source findings below remain separate from clinical interpretation."}</p></Disclosure>
            {p.assessment?.uncertainty ? <p className="small"><strong>Open clinical uncertainty:</strong> {p.assessment.uncertainty}</p> : null}
            <Disclosure title="Patient goals and preferences"><p className="small">{p.discussion?.goals || "Not documented. Discuss goals, preferences and practical constraints before approving a plan."}</p></Disclosure>
          </div>
          <div className="decision-spotlight"><h3>Current decision</h3>
            {plans.isLoading ? <p className="small">Loading plan…</p> : plans.error ? <p role="alert">Plan status unavailable. Open Plan & decisions to retry.</p> : current ? <><div className="row"><Badge value={current.currency.status} /><span className="small">Signed plan v{current.plan.version_no}</span></div><p className="small">{current.plan.intent}</p><p className="small">{words(current.disposition ?? "active")}</p><Link className="small" href={`/w/${workspaceId}/department/protocols/${current.plan.protocol_version_id}`}>Shared protocol used by this plan</Link></> : <p className="small">No signed plan yet. Review the case, discuss goals, assess a published protocol and document the individual decision.</p>}
            {pending ? <p className="small">Plan v{pending.plan.version_no} is {words(pending.plan.status)}.</p> : null}
            <p className="decision-action"><Link className="button-link button-link-primary" href={`${base}/decisions`} aria-label="Review applicability, exceptions and plan">Review plan</Link></p>
          </div>
        </div>
        <div className="overview-support">
          <div><h3>Information awaited</h3><p className="small">{awaited.length || unavailable.length ? `${awaited.length} expected inputs and ${unavailable.length} unavailable biology results recorded.` : "No pending investigation recorded. This does not establish that the workup is complete."}</p>{awaited.length || unavailable.length ? <Disclosure title="View pending information">{awaited.map((u, i) => <p className="small" key={i}>{u.text}</p>)}{unavailable.map((o) => <p className="small" key={o.id}>{o.analyte}: {o.value_text || words(o.result_state)}</p>)}</Disclosure> : null}<Link className="small" href={`${base}/sources#readiness`}>Review reports and missing information</Link></div>
          <div><h3>Follow-up & concerns</h3>{followups.isLoading || concerns.isLoading ? <p className="small">Loading follow-up…</p> : followups.error || concerns.error ? <p className="small" role="alert">Follow-up or concern status unavailable.</p> : <><p className="small">{openFollowups.length} open follow-up obligations. {openConcerns.length} open concerns.</p>{openFollowups.length ? <Disclosure title="View follow-up duties">{openFollowups.map((o) => <p className="small" key={o.id}>{o.purpose}<br />{day(o.due)} · {o.owner_name} <Badge value={o.state} /></p>)}</Disclosure> : null}</>}<Link className="small" href={`${base}/care`}>Open care, concerns and follow-up</Link></div>
          <div><h3>Research for this case</h3><p className="small">Start from an uncertainty in this case, then review the evidence and its limits.</p><Link className="small" href={`/w/${workspaceId}/research?patient=${patientId}`}>Review evidence or ask a case-linked question</Link>{linkedQuestions.length ? <Disclosure title={`Linked questions (${linkedQuestions.length})`}>{linkedQuestions.map((q) => <p className="small" key={q.id}><Link href={`/w/${workspaceId}/research/${q.id}`}>{q.title}</Link> · {q.conclusion ? words(q.conclusion) : "open"}</p>)}</Disclosure> : null}</div>
        </div>
      </Card>
      <div className="grid grid-2">
        <Card title="Disease and recorded burden" testId="disease-burden">
          <p className="hint">Source-verified findings. No stage or remission category is inferred.</p>
          {burden.length ? <>{burden.slice(0, 2).map(finding)}{burden.length > 2 ? <Disclosure title={`More recorded findings (${burden.length - 2})`}>{burden.slice(2).map(finding)}</Disclosure> : null}</> : <p className="small">No source-verified disease assessment yet. Review the received reports before recording the clinical interpretation.</p>}
        </Card>
        <Card title="Treatment received and recorded outcomes" testId="treatment-outcomes">
          <p className="hint">Reported treatment is distinct from a proposed plan.</p>
          {course.length ? <>{course.filter((o) => ["Treatment received", "Reported response"].includes(o.analyte)).map(finding)}<Disclosure title="Treatment period, complications and detail">{course.filter((o) => !["Treatment received", "Reported response"].includes(o.analyte)).map(finding)}</Disclosure></> : <p className="small">No source-verified treatment course or response assessment recorded. A proposed plan does not establish that treatment was given.</p>}
        </Card>
      </div>
      <Disclosure title="How this patient journey works"><ol className="small"><li>Coordinator verifies identity and source findings; the oncologist records assessment and patient goals.</li><li>The research lead appraises published evidence; an independent reviewer approves or objects.</li><li>The lead authors and publishes the shared protocol and SOP after review.</li><li>The treating oncologist assesses applicability, records any exception, and signs the patient’s individual plan.</li><li>The care team accepts tasks and records actual care; follow-up and concerns return to a named owner.</li><li>New reports or protocol changes trigger a review of affected patients.</li></ol></Disclosure>
    </>
  );
}
