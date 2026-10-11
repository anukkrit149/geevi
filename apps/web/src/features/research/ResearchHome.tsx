"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, TextArea, TextInput } from "@/components/ui";
import { api, fileToBase64 } from "@/lib/api/client";
import { useScenario, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

export function ResearchHome({ workspaceId }: { workspaceId: string }) {
  const { can } = useWorkspace(workspaceId);
  const router = useRouter();
  const ws = { workspace_id: workspaceId };
  const questions = useWs(workspaceId, ["research", "questions"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/questions", { params: { path: ws } }));
  const sources = useWs(workspaceId, ["research", "sources"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/sources", { params: { path: ws } }));
  const scenario = useScenario();
  const action = useAction(workspaceId);
  const fileRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState({ title: "", question: "", scope: "", intended_use: "" });
  const [src, setSrc] = useState({ title: "", citation: "" });

  async function createQuestion() {
    const done = await action.run("question", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/questions", { params: { path: ws }, body: { command_id, ...q } }), "Research question opened");
    if (done?.target) router.push(`/w/${workspaceId}/research/${done.target.id}`);
  }
  async function addSource() {
    const file = fileRef.current?.files?.[0];
    const content_base64 = file ? await fileToBase64(file) : null;
    const done = await action.run("source", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/sources", { params: { path: ws },
      body: { command_id, title: src.title, citation: src.citation, source_label: "synthetic", filename: file?.name ?? null, media_type: file ? file.type : null, content_base64 } }), "Evidence source added to the library");
    if (done) {
      setSrc({ title: "", citation: "" });
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <>
      <div className="page-head"><div><h1>Research</h1><p>Questions, cited evidence and independently reviewed appraisals. Accepting evidence publishes no protocol and recommends nothing for any patient.</p></div></div>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      <Card title="Research questions" testId="questions">
        {questions.data?.length ? questions.data.map((item) => (
          <div className="item" key={item.id}>
            <div className="row"><Link className="item-title" href={`/w/${workspaceId}/research/${item.id}`}>{item.title}</Link><Badge value={item.status === "open" ? "open" : "closed"} label={item.conclusion ? words(item.conclusion) : item.status} /></div>
            <p className="small">Owner {item.owner_name} · intended use: {item.intended_use}</p>
          </div>
        )) : <Empty>No research questions yet.</Empty>}
      </Card>
      {can("evidence.author") ? (
        <div className="grid grid-2">
          <Card title="Open a research question" testId="question-form">
            {scenario.data ? (
              <div className="row">
                {(["question_v1", "question_v2", "question_insufficient"] as const).map((key, i) => (
                  <Button variant="quiet" key={key} onClick={() => setQ(scenario.data!.research[key])}>Insert fictional question {i + 1}</Button>
                ))}
              </div>
            ) : null}
            <form onSubmit={(e) => { e.preventDefault(); void createQuestion(); }}>
              <TextInput label="Title" value={q.title} onChange={(title) => setQ({ ...q, title })} required />
              <TextArea label="Question" value={q.question} onChange={(question) => setQ({ ...q, question })} required rows={2} />
              <TextInput label="Scope" value={q.scope} onChange={(scope) => setQ({ ...q, scope })} required />
              <TextInput label="Intended use" value={q.intended_use} onChange={(intended_use) => setQ({ ...q, intended_use })} required />
              <Button variant="primary" type="submit" busy={action.pending === "question"}>Open question</Button>
            </form>
          </Card>
          <Card title="Evidence library" testId="evidence-library">
            {sources.data?.length ? sources.data.map((item) => (
              <div className="item" key={item.id}>
                <div className="row"><strong>{item.title}</strong><Badge value={item.status === "active" ? "current" : item.status} label={`v${item.version_no} · ${item.status}`} /><Badge value="pending" label={words(item.source_label)} /></div>
                <p className="small">{item.citation}</p>
                <p className="small">{item.passages.length} citable passages{item.sha256 ? ` · sha256 ${item.sha256.slice(0, 12)}…` : " · citation only"}</p>
              </div>
            )) : <Empty>No evidence sources yet.</Empty>}
            <form onSubmit={(e) => { e.preventDefault(); void addSource(); }}>
              <fieldset>
                <legend>Add an evidence source</legend>
                <TextInput label="Source title" value={src.title} onChange={(title) => setSrc({ ...src, title })} required />
                <TextArea label="Citation" value={src.citation} onChange={(citation) => setSrc({ ...src, citation })} required rows={2} />
                <div className="field"><label htmlFor="evidence-file">Evidence file (PDF, optional)</label><input id="evidence-file" ref={fileRef} type="file" accept="application/pdf" /></div>
                <Button type="submit" busy={action.pending === "source"}>Add source</Button>
              </fieldset>
            </form>
          </Card>
        </div>
      ) : null}
    </>
  );
}
