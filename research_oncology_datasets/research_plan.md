# Dataset research and complete workflow planning

Date: 11 October 2026. User explicitly requests a complete plan and dataset research, with no application coding.

## Decisions to support
1. Define one complete patient journey connected to a shared departmental protocol, research appraisal, approval, patient-specific exceptions and follow-up.
2. Identify accessible oncology data and authentic document structures to replace overly simplified report assumptions.
3. Recommend a staged data strategy that distinguishes standards, synthetic fixtures, real reports, longitudinal records and research cohorts.

## Scope and ownership
- Oncology research datasets: National Cancer Institute Genomic Data Commons, cancer imaging archives and relevant AML sources. Owner: dataset research agent. Verify actual files, patient-level linkage, longitudinal coverage, access/licence and fitness for our use. Maximum 5 substantive searches.
- Document structure and synthetic/clinical-record sources: oncology interoperability standards, reporting templates and realistic synthetic or restricted clinical notes. Owner: structure research agent. Verify current versions, what is sample versus standard versus actual data, access limits. Maximum 5 substantive searches.
- Workflow/data-plan critique: use the prior completed local audit and current unchanged app snapshot to propose role/state/exception/follow-up requirements and report-schema gaps. Owner: workflow agent. Read-only; no app changes; avoid redundant broad audit.
- Parent: integrate findings into a decision-complete master plan, report schema, data acquisition recommendation, acceptance matrix and open clinical decisions.

## Hypotheses
H1: A single openly available dataset is unlikely to contain all reports, care events, evidence decisions and departmental governance needed for this product.
H2: Source documents and specimen-specific findings need separate structures from the current six-dimensional patient summary.
H3: The existing prototype can be extended through shared protocol objects and scoped review dependencies without rebuilding provenance and source review.

## Method and boundaries
Use current official primary dataset/standard documentation. Use indexed search for discovery and gstack browse for actual pages; use read-only fetch fallback on blocked pages and disclose it. Do not apply for restricted access, accept data-use terms, upload patient data, or download large cohorts. Inspect publicly accessible examples/metadata where practical. Sources need retrieval date, access, short excerpt, credibility/recency/bias and limitations. Save findings and source notes in this folder.

Dataset recommendations must distinguish public metadata from downloadable raw files, open data from controlled data, research-only conditions from permitted product use, images from reports and disease snapshots from a full patient journey. No invented patient linkage across unrelated datasets. Synthetic demonstration records remain explicitly synthetic.

## Outputs
Saved dataset comparison and source index; complete implementation plan under plans/oncology-department-journey/; report-and-data specification; phased backlog and acceptance tests; explicit decisions and validation gates. All writes limited to planning/research documents. App code, fixtures and tests remain unchanged.

## Stop criteria
Identify a defensible primary structural reference, a useful real oncology-report source, a longitudinal/synthetic strategy and AML-specific research option with limitations. Do not claim no suitable data exists merely because bounded search did not find it. The final plan separates decisions made now from clinical rules requiring service ownership.
