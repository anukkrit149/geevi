# Oncology department workflow and Oncologic fit

Date: 11 October 2026. Output: cited briefing plus saved report, confirmed by user.

## Decision
Does Oncologic.ai support the user's vision for patient management, patient-specific protocol decisions, research, and departmental standard operating procedures? How does the confirmed local `healthcare/product` prototype fit, and what should be built and validated next?

## Scope and parallel research
1. Oncologic public product: workflows, audience, evidence, demonstrations, boundaries and useful inspiration. Owner: main agent. Maximum 5 searches plus primary-page reading.
2. Clinical daily workflow: case preparation, multidisciplinary decisions, planned versus actual treatment, follow-up, patient participation and exceptions. Owner: clinical research agent. 3–5 searches maximum.
3. Research and protocol governance: evidence appraisal, service adoption, outcome learning, clinical research requirements, senior-expert role and disconfirming evidence. Owner: governance research agent. 3–5 searches maximum.
4. Current prototype: inspect actual implementation and relevant design documents; distinguish implemented interactions, fixtures, mock behavior, proposed features and missing production systems. Owner: prototype agent. Read-only review; no web searches required.

## Falsifiable hypotheses
H1: Oncologic publicly describes meaningful overlap with a longitudinal patient-care and departmental learning loop, rather than only general oncology advice.
H2: A source-linked case and follow-through workspace can address a measurable operational problem without replacing every hospital information system.
H3: The existing prototype demonstrates the central care/research loop, but does not yet implement production clinical governance and integration.
H4: Senior expertise can be reused through approved protocols, but removing senior clinicians from complex case review is unsupported.

## Method
Use gstack browse for web browsing, primary professional/institutional sources and original studies. Preserve citations, retrieval date, short quotations and source-level credibility/recency/bias scores. Vendor descriptions establish claims, not independently proven outcomes. Clinical workflow recommendations remain proposed until tested with a real service. No treatment recommendations for actual patients.

Each agent owns only its findings file and uniquely prefixed source files under sources/. Do not modify the prototype. Parallel agents are authorized by the explicitly invoked web-research and deep-research skills.

Synthesize a capability comparison, an end-to-end workflow with role ownership, a prioritized build plan, and a falsifiable validation study. Separate public evidence, local implementation evidence and proposed design.

## Opposition and risks
Look for protocol exceptions, patient preferences, multidisciplinary oversight, evidence uncertainty, outcome-data confounding, duplicate entry burden, and existing-system overlap. Marketing pages cannot demonstrate accuracy, adoption, security or workflow effectiveness. A static prototype cannot establish production readiness. Public research cannot establish local demand or procurement willingness.

## Stop criteria and audit
Stop when each research strand has adequate primary evidence, meaningful counterevidence and a concrete recommendation or explicit unknown. Track search queries, source pages read, cited sources and failures. Do not multiply sources only to manufacture consensus; fewer than three independent source types means the thesis remains incompletely triangulated. Save individual source notes, a source index, final report, adversarial review and refresh targets.

## Environment
Gortex daemon is running but does not track this workspace; graph tools return a not-tracked error. Local read-only filesystem inspection is used as fallback. User confirmed `healthcare/product` is the intended Claude-built app. Existing project blueprints are inspected before new research.
