"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Books, Chats, Files, Plus } from "@phosphor-icons/react";
import { useRef, useState } from "react";
import { Badge, Button, Card, Empty, ErrorSummary, Select, TextArea, TextInput } from "@/components/ui";
import { ReferencePack } from "./ReferencePack";
import { citationUrl } from "./EvidenceDetail";
import { api, fileToBase64 } from "@/lib/api/client";
import { useScenario, useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { words } from "@/lib/format";
import { useWorkspace } from "@/lib/session/session";

export function ResearchHome({ workspaceId, patientId }: { workspaceId: string; patientId?: string }) {
  const { can } = useWorkspace(workspaceId);
  const router = useRouter();
  const ws = { workspace_id: workspaceId };
  const questions = useWs(workspaceId, ["research", "questions"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/questions", { params: { path: ws } }));
  const sources = useWs(workspaceId, ["research", "sources"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/sources", { params: { path: ws } }));
  const scenario = useScenario();
  const action = useAction(workspaceId);
  const fileRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState({ title: "", question: "", scope: "", intended_use: "" });
  const [src, setSrc] = useState({ title: "", citation: "", source_label: "public_reference" });
  const [search, setSearch] = useState("");
  const [section, setSection] = useState<"references" | "questions" | "library">(patientId ? "references" : "questions");
  function focusQuestion() {
    setSection("questions");
    requestAnimationFrame(() => document.querySelector<HTMLInputElement>('[data-testid="question-form"] input')?.focus());
  }
  const library = sources.data?.filter((s) => `${s.title} ${s.citation}`.toLowerCase().includes(search.toLowerCase())) ?? [];

  async function createQuestion() {
    const done = await action.run("question", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/questions", { params: { path: ws }, body: { command_id, ...q, origin: patientId ? { patient_id: patientId, kind: "case_question" } : null } }), "Research question opened");
    if (done?.target) router.push(`/w/${workspaceId}/research/${done.target.id}`);
  }
  async function addSource() {
    const file = fileRef.current?.files?.[0];
    const content_base64 = file ? await fileToBase64(file) : null;
    const done = await action.run("source", (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/sources", { params: { path: ws },
      body: { command_id, title: src.title, citation: src.citation, source_label: src.source_label as "public_reference" | "synthetic", filename: file?.name ?? null, media_type: file ? file.type : null, content_base64 } }), "Evidence source added to the library");
    if (done) {
      setSrc({ ...src, title: "", citation: "" });
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <>
      <div className="page-head"><div><h1>Research</h1><p>Explore evidence, ask a focused question and follow its review.</p></div>{can("evidence.author") ? <Button variant="primary" onClick={focusQuestion}><Plus aria-hidden="true" />New question</Button> : null}</div>
      <ErrorSummary error={action.error} onDismiss={action.clearError} />
      {patientId ? <Card title="Research linked to this case"><p>The question will keep a link to this patient. Evidence acceptance still requires a separate applicability review before it can inform a patient plan.</p><Link href={`/w/${workspaceId}/patients/${patientId}`}>Return to patient profile</Link></Card> : null}
      <div className="research-tabs" role="group" aria-label="Research view">{([{ key: "questions", label: "Questions", icon: Chats }, { key: "references", label: "Published references", icon: Books }, { key: "library", label: "Evidence library", icon: Files }] as const).map(({ key, label, icon: Icon }) => <button className="filter-chip" key={key} aria-pressed={section === key} aria-controls={`research-${key}`} onClick={() => setSection(key)}><Icon size={18} aria-hidden="true" />{label}</button>)}</div>
      <p className="research-note">Accepting evidence publishes no protocol and recommends nothing for any patient.</p>
      <div id="research-references" hidden={section !== "references"}>
      <ReferencePack workspaceId={workspaceId} onQuestion={(question) => { setQ(question); focusQuestion(); }} />
      </div>
      <div id="research-questions" hidden={section !== "questions"}>
      <Card title="Research questions" testId="questions">
        {questions.isLoading ? <p className="small" role="status">Loading research questions…</p> : questions.error ? <p role="alert">Research questions could not be loaded. <Button onClick={() => questions.refetch()}>Try again</Button></p> : questions.data?.length ? questions.data.map((item) => (
          <div className="item" key={item.id}>
            <div className="row"><Link className="item-title" href={`/w/${workspaceId}/research/${item.id}`}>{item.title}</Link><Badge value={item.status === "open" ? "open" : "closed"} label={item.conclusion ? words(item.conclusion) : item.status} /></div>
            <p className="small">Owner {item.owner_name} · intended use: {item.intended_use}</p>
          </div>
        )) : <Empty>No research questions yet.</Empty>}
      </Card>
      {can("evidence.author") ? (
        <div>
          <Card title="Open a research question" testId="question-form">
            {scenario.data ? (
              <div className="row">
                {(["question_v1", "question_v2", "question_insufficient"] as const).map((key, i) => (
                  <Button variant="quiet" key={key} onClick={() => setQ(scenario.data!.research[key])}>Insert demo question {i + 1}</Button>
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
        </div>
      ) : null}
      </div>
      <div id="research-library" hidden={section !== "library"}>
          <Card title="Evidence library" testId="evidence-library">
            <TextInput label="Find an evidence document" value={search} onChange={setSearch} hint="Search title, citation or publication identifier." />
            {sources.isLoading ? <p role="status">Loading evidence library…</p> : sources.error ? <p role="alert">Evidence library could not be loaded. <Button onClick={() => sources.refetch()}>Try again</Button></p> : library.length ? library.map((item) => (
              <div className="item" key={item.id}>
                <div className="row"><Link href={`/w/${workspaceId}/research/sources/${item.id}`}>{item.title}</Link><Badge value={item.status === "active" ? "current" : item.status} label={`v${item.version_no} · ${item.status}`} /><Badge value="reviewed" label={words(item.source_label)} /></div>
                <p className="small">{item.citation}</p>
                <div className="row"><Link href={`/w/${workspaceId}/research/sources/${item.id}`}>Open evidence document and passages</Link>{citationUrl(item.citation) ? <a href={citationUrl(item.citation)!} target="_blank" rel="noreferrer">Original publication</a> : null}</div>
                <p className="small">{item.passages.length} citable passages{item.sha256 ? ` · sha256 ${item.sha256.slice(0, 12)}…` : " · citation only"}</p>
              </div>
            )) : <Empty>{search ? "No evidence documents match your search. Try a different title or citation." : "No evidence sources yet. Add a source or import a brief from Published references."}</Empty>}
            {can("evidence.author") ? <form onSubmit={(e) => { e.preventDefault(); void addSource(); }}>
              <fieldset>
                <legend>Add an evidence source</legend>
                <TextInput label="Source title" value={src.title} onChange={(title) => setSrc({ ...src, title })} required />
                <TextArea label="Citation" value={src.citation} onChange={(citation) => setSrc({ ...src, citation })} required rows={2} />
                <Select label="Source provenance" value={src.source_label} onChange={(source_label) => setSrc({ ...src, source_label })} options={[{ value: "public_reference", label: "Published public reference" }, { value: "synthetic", label: "Synthetic teaching material" }]} />
                <div className="field"><label htmlFor="evidence-file">Evidence file (PDF, optional)</label><input id="evidence-file" ref={fileRef} type="file" accept="application/pdf" /></div>
                <Button type="submit" busy={action.pending === "source"}>Add source</Button>
              </fieldset>
            </form> : null}
          </Card>
      </div>
    </>
  );
}
