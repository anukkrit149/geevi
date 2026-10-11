"use client";

import { BookOpen, ArrowUpRight } from "@phosphor-icons/react";
import { useState } from "react";
import { Badge, Button, Card, Disclosure, ErrorSummary, TextInput } from "@/components/ui";
import { api } from "@/lib/api/client";
import { useWs } from "@/lib/api/hooks";
import { useAction } from "@/lib/api/useAction";
import { useWorkspace } from "@/lib/session/session";

export function ReferencePack({ workspaceId, onQuestion }: { workspaceId: string; onQuestion: (question: { title: string; question: string; scope: string; intended_use: string }) => void }) {
  const { can } = useWorkspace(workspaceId);
  const refs = useWs(workspaceId, ["research", "reference-pack"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/reference-pack", { params: { path: { workspace_id: workspaceId } } }));
  const sources = useWs(workspaceId, ["research", "sources"], () => api.GET("/api/v1/workspaces/{workspace_id}/research/sources", { params: { path: { workspace_id: workspaceId } } }));
  const action = useAction(workspaceId);
  const [search, setSearch] = useState("");
  const [terms, setTerms] = useState("acute myeloid leukemia diagnostic workup");
  const items = refs.data?.filter((r) => [r.title, r.source_type, r.question, r.population, ...r.search_terms].join(" ").toLowerCase().includes(search.toLowerCase())) ?? [];
  return <Card title="Published AML evidence pack" testId="reference-pack">
    <p className="small">Dated references selected for the demo. Browse by question, then open the study detail. This is not a complete or automatically updated literature review.</p>
    <ErrorSummary error={action.error} />
    <TextInput label="Find evidence in the pack" value={search} onChange={setSearch} hint="Try diagnosis, older adults, venetoclax, genomics or trial eligibility." />
    {refs.error ? <p role="alert">The evidence pack could not be loaded. Reload to retry.</p> : refs.isLoading ? <p>Loading published references…</p> : !items.length ? <p>No matching references in this pack.</p> : items.map((r) => {
      const added = sources.data?.some((s) => s.citation === r.citation && s.status === "active");
      return <div className="item reference-item" key={r.id} data-testid={`reference-${r.id}`}>
        <div className="reference-heading"><BookOpen aria-hidden="true" /><div><strong>{r.title}</strong><div className="row"><Badge value="reviewed" label={r.source_type} /><span className="small">{r.publication_date}</span></div></div></div>
        <p className="small"><strong>Review depth:</strong> {r.access_status} Full methods have not been critically appraised in this starter pack.</p>
        <p className="reference-question">{r.question}</p>
        <Disclosure title="Population, findings and limitations"><p className="small"><strong>Population:</strong> {r.population}</p><p className="small"><strong>Findings:</strong> {r.findings}</p><p className="small"><strong>Limits:</strong> {r.limitations}</p></Disclosure>
        <details><summary>Study structure, applicability and source documentation</summary><p>Intervention: {r.intervention}</p><p>Comparator: {r.comparator}</p><p>Outcomes: {r.outcomes}</p><p>Applicability: {r.applicability}</p><p className="small">{r.citation}</p><p className="small">{r.license_note}</p></details>
        <div className="row"><a href={r.url} target="_blank" rel="noreferrer" className="button-link">Read publication<ArrowUpRight aria-hidden="true" /></a>
          {can("evidence.author") ? <><Button disabled={added} busy={action.pending === r.id} onClick={() => action.run(r.id, (command_id) => api.POST("/api/v1/workspaces/{workspace_id}/research/reference-pack/{reference_id}/import", { params: { path: { workspace_id: workspaceId, reference_id: r.id } }, body: { command_id } }), "Published evidence brief added to the library")}>{added ? "In evidence library" : "Add evidence brief to library"}</Button><Button onClick={() => onQuestion({ title: r.title, question: r.question, scope: `AML evidence review: ${r.population}`, intended_use: "Assess evidence and patient applicability before proposing any departmental change. No individual recommendation is issued." })}>Use as a research question</Button></> : null}
        </div>
      </div>;
    })}
    <Disclosure title="Search beyond the demo pack"><fieldset><legend>Literature search</legend><TextInput label="Literature search terms" value={terms} onChange={setTerms} hint="Use disease, population, intervention and outcome terms. Do not enter patient names, identifiers or report text." /><div className="row"><a href={`https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(terms)}`} target="_blank" rel="noreferrer">Search PubMed</a><a href={`https://clinicaltrials.gov/search?cond=Acute%20Myeloid%20Leukemia&term=${encodeURIComponent(terms)}`} target="_blank" rel="noreferrer">Search ClinicalTrials.gov</a></div><p className="small">These searches open the source website. Results are not automatically imported, appraised or matched to patients.</p></fieldset></Disclosure>
  </Card>;
}
