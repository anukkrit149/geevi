"use client";

import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Loading, Meta, Select, TextArea, TextInput } from "@/components/ui";
import { api, type Schemas } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { day, valueWithUnits, words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";
import { SourceViewer, type Highlight } from "./SourceViewer";

type Candidate = Schemas["ExtractionCandidateOut"];
const STATES = ["reported_value", "detected", "not_detected", "pending", "untested", "indeterminate", "insufficient_sample", "unreported", "unavailable"];
const DIMENSIONS = ["biology", "extent", "fitness", "history", "current", "priorities"];

function refToHighlight(ref: Record<string, any>, label: string): Highlight | null {
  if (!ref?.region) return null;
  return { page: ref.page ?? 1, region: ref.region, pageSize: ref.page_size ?? null, units: ref.units ?? (ref.page_size ? "page-points" : "fraction"), label };
}

export function SourceReview({ workspaceId, patientId, documentId }: { workspaceId: string; patientId: string; documentId: string }) {
  const { can } = useWorkspace(workspaceId);
  const search = useSearchParams();
  const bundle = useWs(workspaceId, ["patient", patientId, "source", documentId], () =>
    api.GET("/api/v1/workspaces/{workspace_id}/sources/{document_id}", { params: { path: { workspace_id: workspaceId, document_id: documentId } } }));
  const action = useAction(workspaceId);
  const [highlight, setHighlight] = useState<Highlight | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [inspected, setInspected] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<{ id: string; mode: "corrected" | "rejected" | "unresolved"; value_text: string; result_state: string; reason: string } | null>(null);
  const [assoc, setAssoc] = useState({ checked: false, note: "", rejectReason: "" });
  const [selecting, setSelecting] = useState(false);
  const [manual, setManual] = useState({ page: "1", region: ["", "", "", ""], analyte: "", dimension: "current", exact_wording: "", value_text: "", units: "", result_state: "reported_value" });

  // Exact deep link from the profile: ?observation=<id> opens the original at that finding's region.
  const linked = bundle.data?.observations.find((o) => o.id === search.get("observation")) ?? null;
  const linkedHighlight = useMemo(() => (linked ? refToHighlight(linked.source_ref, linked.exact_wording) : null), [linked]);
  const shownHighlight = highlight ?? linkedHighlight;
  const shownActive = active ?? linked?.candidate_id ?? null;

  if (bundle.isLoading) return <Loading what="document" />;
  if (!bundle.data) return <div className="card" role="alert" data-testid="record-unavailable">This document is not available in this workspace.</div>;
  const { document: doc, reports, specimens, candidates, observations, reviews } = bundle.data;
  const path = { workspace_id: workspaceId };
  const associated = doc.association_status === "associated";
  const page = (doc.pages as { number: number; width: number; height: number }[]).find((p) => p.number === Number(manual.page));

  function inspect(c: Candidate) {
    setHighlight(refToHighlight(c.source_ref, String(c.assertion.exact_wording ?? "")));
    setActive(c.id);
    setInspected((s) => new Set(s).add(c.id));
  }
  async function review(c: Candidate, disposition: string, extra: Record<string, unknown> = {}) {
    const done = await action.run(`review:${c.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/candidates/{candidate_id}/review", {
      params: { path: { ...path, candidate_id: c.id } },
      body: { command_id, expected_revision: c.revision, disposition: disposition as never, source_inspected: inspected.has(c.id), ...extra },
    }), `${String(c.assertion.analyte)}: source review recorded (${disposition})`);
    if (done) setEditing(null);
  }
  async function addManual() {
    const fraction = manual.region.map(Number);
    const region = page ? [fraction[0] * page.width, fraction[1] * page.height, fraction[2] * page.width, fraction[3] * page.height] : fraction;
    const done = await action.run("manual", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/sources/{document_id}/candidates", {
      params: { path: { ...path, document_id: documentId } },
      body: { command_id, page: Number(manual.page), region, analyte: manual.analyte, dimension: manual.dimension as never, exact_wording: manual.exact_wording,
        value_text: manual.value_text || null, units: manual.units || null, result_state: manual.result_state as never },
    }), "Manual source-linked finding added for review");
    if (done) {
      setManual((m) => ({ ...m, region: ["", "", "", ""], analyte: "", exact_wording: "", value_text: "", units: "" }));
      setSelecting(false);
    }
  }

  return (
    <>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      <Card title={doc.title} testId="document-head" actions={<Badge value={doc.association_status} />}>
        <Meta items={[["Issuer", doc.issuer], ["Accession", doc.external_id], ["Report type", words(doc.doc_kind)], ["Received", day(doc.received_time)],
          ["Recorded by", doc.recorded_by_name], ["Original SHA-256", <span className="mono" key="sha">{doc.sha256}</span>], ["Bytes", doc.length]]} />
        {reports.map((r) => (
          <p className="small" key={r.id} data-testid="report-relation">
            Report version {r.version_no}: <Badge value={r.relation_kind === "original" ? "current" : "corrected"} label={words(r.relation_kind)} /> issued status “{r.issued_status}”
            {r.scope_note ? ` · ${r.scope_note}` : ""}{r.affected_scope?.length ? ` · affects: ${r.affected_scope.join(", ")}` : ""}
          </p>
        ))}
        {specimens.length ? <p className="small">Specimens: {specimens.map((s) => `${s.label} — ${s.material ?? "not described"}`).join(" · ")}</p> : null}
        {doc.extraction_limits?.note ? <p className="small"><strong>Extraction limits:</strong> {String(doc.extraction_limits.note)}</p> : null}
      </Card>

      {!associated ? (
        <Card title="Identity and association review" testId="association" tone="warn">
          <p>
            {doc.association_status === "quarantined"
              ? <>This document is <strong>quarantined</strong>: it names the identifier “{String(doc.claimed_identity?.value ?? "none")}”, which does not match the intended patient.</>
              : <>The document names the identifier “{String(doc.claimed_identity?.value ?? "none found")}”. Confirm it belongs to this patient before any finding is reviewed.</>}
          </p>
          {can("source.import") && doc.association_status !== "rejected" ? (
            <>
              <label className="check"><input type="checkbox" checked={assoc.checked} onChange={(e) => setAssoc({ ...assoc, checked: e.target.checked })} />
                I checked the patient, specimen and report context against the original.</label>
              <TextArea label="How was identity verified?" value={assoc.note} onChange={(note) => setAssoc({ ...assoc, note })} rows={2} />
              <div className="row">
                <Button variant="primary" busy={action.pending === "associate"} onClick={() => action.run("associate", (command_id) =>
                  api.POST("/api/v1/workspaces/{workspace_id}/sources/{document_id}/associate", { params: { path: { ...path, document_id: documentId } },
                    body: { command_id, expected_revision: doc.revision, patient_id: patientId, checked: assoc.checked, note: assoc.note } }), "Document associated with the patient")}>
                  Associate with this patient
                </Button>
              </div>
              <details style={{ marginTop: ".6rem" }}>
                <summary>Reject this document</summary>
                <TextArea label="Reason for rejection" value={assoc.rejectReason} onChange={(rejectReason) => setAssoc({ ...assoc, rejectReason })} rows={2} />
                <Button variant="danger" onClick={() => action.run("reject", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/sources/{document_id}/reject", {
                  params: { path: { ...path, document_id: documentId } }, body: { command_id, expected_revision: doc.revision, reason: assoc.rejectReason } }), "Document rejected")}>Reject</Button>
              </details>
            </>
          ) : <p className="small">An account with the source intake grant completes this review.</p>}
        </Card>
      ) : null}

      <div className="viewer">
        <div>
          <SourceViewer contentPath={`/api/v1/workspaces/${workspaceId}/sources/${documentId}/content`} mediaType={doc.media_type ?? null}
            available={doc.original_available} highlight={shownHighlight} selecting={selecting}
            onSelect={(p, region) => setManual((m) => ({ ...m, page: String(p), region: region.map(String) }))}
            fallbackText={(doc.legacy as { pages?: string[] } | null)?.pages ?? null} />
        </div>
        <div>
          <Card title={`Candidate findings (${candidates.length})`} testId="candidates" level={3}>
            <p className="small">Source review checks the wording against the original region. It is not a clinical interpretation.</p>
            {candidates.length ? candidates.map((c) => {
              const a = c.assertion as Record<string, any>;
              const hasRegion = !!(c.source_ref as Record<string, any>).region;
              return (
                <div className="candidate" key={c.id} data-active={shownActive === c.id} data-testid={`candidate-${a.analyte}`}>
                  <div className="row"><strong>{a.analyte}</strong><Badge value={c.status} />{a.specimen_label ? <span className="small">{a.specimen_label}</span> : null}
                    {c.manual ? <Badge value="corrected" label="manual entry" /> : null}</div>
                  <p className="quote">{a.exact_wording}</p>
                  <p className="small">Read as: {valueWithUnits(a.value_text, a.units)} · state <Badge value={a.result_state === "reported_value" ? "current" : "pending"} label={words(a.result_state)} />
                    {a.legacy ? ` · legacy status: ${a.legacy.status}` : ""}</p>
                  <div className="row">
                    <Button onClick={() => inspect(c)} disabled={!hasRegion || !doc.original_available} aria-pressed={inspected.has(c.id)}>
                      {inspected.has(c.id) ? "Source inspected" : "Inspect source"}
                    </Button>
                    {can("source.review") && associated && c.status === "unreviewed" ? (
                      <>
                        <Button variant="primary" busy={action.pending === `review:${c.id}`} onClick={() => review(c, "verified")}>Verify</Button>
                        <Button onClick={() => setEditing({ id: c.id, mode: "corrected", value_text: a.value_text ?? "", result_state: a.result_state, reason: "" })}>Correct…</Button>
                        <Button onClick={() => setEditing({ id: c.id, mode: "rejected", value_text: "", result_state: a.result_state, reason: "" })}>Reject…</Button>
                      </>
                    ) : null}
                  </div>
                  {!hasRegion ? <p className="small">No source geometry was captured for this finding, so it cannot be verified.</p> : null}
                  {editing?.id === c.id ? (
                    <fieldset style={{ marginTop: ".5rem" }}>
                      <legend>{editing.mode === "corrected" ? "Correct the transcription" : "Reject this candidate"}</legend>
                      {editing.mode === "corrected" ? (
                        <>
                          <TextInput label="Corrected value text" value={editing.value_text} onChange={(value_text) => setEditing({ ...editing, value_text })} />
                          <Select label="Result state as stated by the source" value={editing.result_state} onChange={(result_state) => setEditing({ ...editing, result_state })}
                            options={STATES.map((s) => ({ value: s, label: words(s) }))} />
                        </>
                      ) : null}
                      <TextArea label="Reason" value={editing.reason} onChange={(reason) => setEditing({ ...editing, reason })} rows={2}
                        hint="A local correction changes this app's transcription history, not the laboratory's report." />
                      <div className="row">
                        <Button variant="primary" onClick={() => review(c, editing.mode, { reason: editing.reason,
                          corrected: editing.mode === "corrected" ? { value_text: editing.value_text, result_state: editing.result_state } : null })}>Record {editing.mode}</Button>
                        <Button onClick={() => setEditing(null)}>Cancel</Button>
                      </div>
                    </fieldset>
                  ) : null}
                </div>
              );
            }) : <Empty>No candidates were extracted. Use manual source-linked entry below.</Empty>}
          </Card>

          {can("source.review") && associated && doc.original_available ? (
            <Card title="Manual source-linked entry" testId="manual-entry" level={3}>
              <p className="small">For image-only or unsupported layouts: mark the region on the page (drag) or type its bounds, then transcribe exactly.</p>
              <div className="row">
                <Button aria-pressed={selecting} onClick={() => setSelecting((v) => !v)}>{selecting ? "Stop selecting" : "Select region on page"}</Button>
              </div>
              <fieldset>
                <legend>Region (fractions of the page, 0–1)</legend>
                <div className="row">
                  {["Left", "Top", "Right", "Bottom"].map((label, i) => (
                    <div className="field" key={label} style={{ width: 90 }}>
                      <label htmlFor={`region-${i}`}>{label}</label>
                      <input id={`region-${i}`} inputMode="decimal" value={manual.region[i]} onChange={(e) => setManual((m) => ({ ...m, region: m.region.map((v, j) => (j === i ? e.target.value : v)) }))} />
                    </div>
                  ))}
                </div>
              </fieldset>
              <TextInput label="Finding name" value={manual.analyte} onChange={(analyte) => setManual({ ...manual, analyte })} />
              <TextInput label="Exact wording on the page" value={manual.exact_wording} onChange={(exact_wording) => setManual({ ...manual, exact_wording })} />
              <div className="grid grid-3">
                <TextInput label="Value text" value={manual.value_text} onChange={(value_text) => setManual({ ...manual, value_text })} />
                <TextInput label="Units" value={manual.units} onChange={(units) => setManual({ ...manual, units })} />
                <Select label="Result state" value={manual.result_state} onChange={(result_state) => setManual({ ...manual, result_state })} options={STATES.map((s) => ({ value: s, label: words(s) }))} />
                <Select label="Profile dimension" value={manual.dimension} onChange={(dimension) => setManual({ ...manual, dimension })} options={DIMENSIONS.map((d) => ({ value: d, label: d }))} />
              </div>
              <Button variant="primary" busy={action.pending === "manual"} onClick={addManual}>Add finding for review</Button>
            </Card>
          ) : null}

          <Card title="Recorded observations and review history" testId="observations" level={3}>
            {observations.length ? observations.map((o) => (
              <div className="item" key={o.id}>
                <div className="row"><strong>{o.analyte}</strong><span>{valueWithUnits(o.value_text, o.units)}</span><Badge value={o.status} />
                  <span className="small">v{o.version_no}{o.specimen_label ? ` · ${o.specimen_label}` : ""} · {day(o.effective_time)}</span></div>
                {o.superseded_reason ? <p className="small">{o.superseded_reason}</p> : null}
                {(o.normalization as Record<string, any>)?.note ? <p className="small">{String((o.normalization as Record<string, any>).note)}</p> : null}
              </div>
            )) : <Empty>No observations recorded from this document yet.</Empty>}
            {reviews.length ? <p className="small">Reviews: {reviews.map((r) => `${r.disposition} by ${r.recorded_by_name}`).join(" · ")}</p> : null}
          </Card>
        </div>
      </div>
    </>
  );
}
