"use client";

import { useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Loading, Meta, Select, TextArea, TextInput } from "@/components/ui";
import { ReviewPanel } from "@/features/department/ReviewPanel";
import { api, type Schemas } from "@/lib/api/client";
import { useMembers, useScenario, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { when, words } from "@/lib/format";
import { useSession, useWorkspace } from "@/lib/session/session";

type Appraisal = Schemas["EvidenceAppraisalOut"];
type Source = Schemas["EvidenceSourceOut"];
const FIELDS: [string, string][] = [["population", "Population (as reported)"], ["intervention", "Intervention"], ["comparator", "Comparator"], ["outcome", "Outcome"],
  ["timepoint", "Timepoint"], ["study_design", "Study design (as reported)"], ["findings", "Findings"], ["uncertainty", "Uncertainty"], ["limitations", "Limitations"]];
type Content = Record<string, string>;
type Citation = { source_id: string; passage_id: string };

function AppraisalEditor({ workspaceId, questionId, appraisal, sources }: { workspaceId: string; questionId: string; appraisal: Appraisal | null; sources: Source[] }) {
  const scenario = useScenario();
  const members = useMembers(workspaceId);
  const action = useAction(workspaceId);
  const [content, setContent] = useState<Content>((appraisal?.content as Content) ?? Object.fromEntries(FIELDS.map(([k]) => [k, ""])));
  const [citations, setCitations] = useState<Citation[]>((appraisal?.citations as Citation[]) ?? []);
  const [base, setBase] = useState(appraisal?.revision ?? 0);
  const [id, setId] = useState(appraisal?.id ?? null);
  const active = sources.filter((s) => s.status === "active");
  const [sourceId, setSourceId] = useState("");
  const source = active.find((s) => s.id === (sourceId || citations[0]?.source_id)) ?? active[0];
  const reviewers = (members.data ?? []).filter((m) => m.capabilities.includes("evidence.review"));
  const [reviewer, setReviewer] = useState("");
  const cited = (passageId: string) => citations.some((c) => c.source_id === source?.id && c.passage_id === passageId);
  const body = () => ({ ...content, citations });

  async function save(): Promise<{ id: string; revision: number } | null> {
    const done = id
      ? await action.run("save", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/appraisals/{appraisal_id}/save", {
        params: { path: { workspace_id: workspaceId, appraisal_id: id } }, body: { command_id, expected_revision: base, ...body() } as never }), "Appraisal draft saved")
      : await action.run("start", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/questions/{question_id}/appraisals", {
        params: { path: { workspace_id: workspaceId, question_id: questionId } }, body: { command_id, ...body() } as never }), "Appraisal draft created");
    if (!done?.target) return null;
    setId(done.target.id);
    setBase(done.target.revision);
    return { id: done.target.id, revision: done.target.revision };
  }
  async function submit() {
    const saved = await save();
    if (!saved) return;
    await action.run("submit", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/appraisals/{appraisal_id}/submit", {
      params: { path: { workspace_id: workspaceId, appraisal_id: saved.id } }, body: { command_id, expected_revision: saved.revision, reviewer_username: reviewer || reviewers[0]?.username || null } }),
      "Appraisal frozen and submitted for independent review");
  }

  return (
    <div data-testid="appraisal-editor">
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {scenario.data ? (
        <div className="row">
          <Button variant="quiet" onClick={() => setContent(scenario.data!.research.appraisal_v1)}>Insert fictional appraisal 1</Button>
          <Button variant="quiet" onClick={() => setContent(scenario.data!.research.appraisal_v2)}>Insert fictional appraisal 2</Button>
        </div>
      ) : null}
      <div className="grid grid-2">
        {FIELDS.map(([key, label]) => <TextArea key={key} label={label} rows={2} value={content[key] ?? ""} onChange={(v) => setContent({ ...content, [key]: v })} />)}
      </div>
      <fieldset data-testid="passages">
        <legend>Cited source passages ({citations.length} cited)</legend>
        {active.length ? (
          <>
            <Select label="Evidence source" value={source?.id ?? ""} onChange={setSourceId} options={active.map((s) => ({ value: s.id, label: `${s.title} (v${s.version_no})` }))} />
            {source?.passages.length ? (source.passages as Record<string, any>[]).map((p) => (
              <label className="check" key={p.id}>
                <input type="checkbox" checked={cited(p.id)} onChange={(e) => setCitations(e.target.checked ? [...citations, { source_id: source.id, passage_id: p.id }]
                  : citations.filter((c) => !(c.source_id === source.id && c.passage_id === p.id)))} />
                <span>{p.text} <span className="small">(page {p.page})</span></span>
              </label>
            )) : <p className="small">This source has no text passages (citation only).</p>}
          </>
        ) : <p className="small">Add an evidence source in the library first.</p>}
      </fieldset>
      <div className="row" style={{ alignItems: "flex-end" }}>
        <Button busy={action.pending === "save" || action.pending === "start"} onClick={() => void save()} style={{ marginBottom: ".6rem" }}>Save draft</Button>
        <Select label="Independent reviewer" value={reviewer || reviewers[0]?.username || ""} onChange={setReviewer}
          options={reviewers.length ? reviewers.map((m) => ({ value: m.username, label: m.display_name })) : [{ value: "", label: "No account holds the review grant" }]} />
        <Button variant="primary" busy={action.pending === "submit"} onClick={() => void submit()} style={{ marginBottom: ".6rem" }}>Save and submit for independent review</Button>
      </div>
    </div>
  );
}

export function QuestionDetail({ workspaceId, questionId }: { workspaceId: string; questionId: string }) {
  const { can } = useWorkspace(workspaceId);
  const { session } = useSession();
  const ws = { workspace_id: workspaceId };
  const detail = useWs(workspaceId, ["research", "question", questionId], () => api.GET("/api/v1/workspaces/{workspace_id}/research/questions/{question_id}", { params: { path: { ...ws, question_id: questionId } } }));
  const sources = useWs(workspaceId, ["research", "sources"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/sources", { params: { path: ws } }));
  const action = useAction(workspaceId);
  const [conclusion, setConclusion] = useState({ value: "insufficient_evidence", note: "" });
  if (detail.isLoading) return <Loading what="research question" />;
  if (!detail.data) return <div className="card" role="alert" data-testid="record-unavailable"><h1>Record not available</h1><p>This research question does not exist in this workspace.</p></div>;
  const { question, appraisals, reviews } = detail.data;
  const draft = appraisals.find((a) => a.status === "draft" && a.recorded_by === session?.account.id) ?? null;
  const inFlight = appraisals.some((a) => ["draft", "in_review"].includes(a.status));
  const owner = question.owner_id === session?.account.id;
  const passageText = (c: Citation) => (sources.data ?? []).flatMap((s) => (s.id === c.source_id ? (s.passages as Record<string, any>[]) : [])).find((p) => p.id === c.passage_id)?.text;

  return (
    <>
      <div className="page-head">
        <div><h1>{question.title}</h1><p>{question.question}</p></div>
        <span data-testid="question-status"><Badge value={question.status === "open" ? "open" : "closed"} label={question.conclusion ? words(question.conclusion) : "open"} /></span>
      </div>
      <Card title="Question" testId="question">
        <Meta items={[["Scope", question.scope], ["Intended use", question.intended_use], ["Owner", question.owner_name], ["Opened", when(question.recorded_at)],
          ["Conclusion", question.conclusion ? `${words(question.conclusion)} — ${question.conclusion_note}` : null]]} />
        <p className="small">{detail.data.recommendation_notice}</p>
      </Card>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      <Card title="Evidence appraisals" testId="appraisals">
        {appraisals.length ? appraisals.filter((a) => a.id !== draft?.id).map((a) => (
          <div className="item" key={a.id} data-testid={`appraisal-${a.status}`}>
            <div className="row"><strong>Appraisal v{a.version_no}</strong><Badge value={a.status} />{a.review_needed ? <Badge value="review_needed" label="review needed" /> : null}
              <span className="small">author {a.recorded_by_name}</span></div>
            <p className="quote">{String((a.content as Content).findings)}</p>
            <p className="small">Design: {String((a.content as Content).study_design)} · Limitations: {String((a.content as Content).limitations)}</p>
            {(a.citations as Citation[]).map((c) => <p className="small" key={c.passage_id}>Cites: “{passageText(c) ?? c.passage_id}”</p>)}
            {a.review_needed_reason ? <p className="small">⚠ {a.review_needed_reason}</p> : null}
            {can("evidence.author") && a.recorded_by === session?.account.id && ["accepted", "changes_requested"].includes(a.status) && !inFlight && question.status === "open" ? (
              <Button onClick={() => action.run(`revise:${a.id}`, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/appraisals/{appraisal_id}/revise", {
                params: { path: { ...ws, appraisal_id: a.id } }, body: { command_id } }), "Successor draft opened; the earlier version is retained")}>Open successor revision</Button>
            ) : null}
          </div>
        )) : !draft ? <Empty>No appraisal has been drafted.</Empty> : null}
        {can("evidence.author") && question.status === "open" && (draft || !inFlight) && (draft || !appraisals.some((a) => ["accepted", "changes_requested"].includes(a.status))) ? (
          <div className="item"><strong>{draft ? `Draft appraisal v${draft.version_no}` : "New appraisal"}</strong>
            <AppraisalEditor key={draft?.id ?? "new"} workspaceId={workspaceId} questionId={questionId} appraisal={draft} sources={sources.data ?? []} /></div>
        ) : null}
      </Card>
      <Card title="Independent review and disagreement history" testId="reviews"><ReviewPanel workspaceId={workspaceId} reviews={reviews} /></Card>
      {owner && question.status === "open" ? (
        <Card title="Conclude this question" testId="conclude">
          <Select label="Conclusion" value={conclusion.value} onChange={(value) => setConclusion({ ...conclusion, value })}
            options={[{ value: "insufficient_evidence", label: "Insufficient evidence (no protocol change, no recommendation)" }, { value: "evidence_accepted", label: "Evidence accepted into the library" }]} />
          <TextInput label="Reasoning" value={conclusion.note} onChange={(note) => setConclusion({ ...conclusion, note })} />
          <Button busy={action.pending === "conclude"} onClick={() => action.run("conclude", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/questions/{question_id}/conclude", {
            params: { path: { ...ws, question_id: questionId } }, body: { command_id, expected_revision: question.revision, conclusion: conclusion.value as never, note: conclusion.note } }), "Question concluded")}>Conclude question</Button>
        </Card>
      ) : null}
    </>
  );
}
