# Coding-agent handoff: new FastAPI and Next.js application

11 October 2026. The user changed the architecture. Build a new application; the vanilla app is a reference. This planning run has not written application code.

Copy the following prompt into a coding agent working in this `healthcare` workspace:

> Build a NEW oncology department application from scratch using **Next.js App Router, React and TypeScript for the frontend**, **FastAPI/Pydantic for the backend**, and **PostgreSQL with SQLAlchemy/Psycopg/Alembic for persistence**. Next.js is the chosen frontend; do not substitute a standalone React/Vite app or extend the vanilla JavaScript app. Create the new application under `apps/web/` and `apps/api/` in this repository.
>
> Read and implement `docs/plans/2026-10-11-1137-feat-oncology-department-journey-plan.md`, revision 2. Its Product Contract governs behavior; its Planning Contract, implementation units U1–U14, Verification Contract and Definition of Done govern implementation. Follow the dependency graph: U3 precedes U2 even though stable unit IDs retain their original numbering.
>
> Deliver the complete fictional Meera journey and Arun's independent use of a shared departmental protocol: realistic separate source reports, longitudinal patient context and source verification; research question, appraisal and independent review; protocol and separate SOP publication; patient applicability/discussion, exceptions and exact plan approval; accepted handoff tasks, attributed actual care, concerns and routine follow-up; reviewed protocol v2 and independently resolved patient impacts. Include original preservation, explicit legacy import, scoped review currency, atomic persistence and complete backup/staged restore.
>
> Keep `product/` and its browser data unchanged. Study useful behavior, sources and tests as references; reimplement with new Python/TypeScript modules. Do not import IIFE scripts, rely on old localStorage/IndexedDB or treat old test results as verification of this app. Old exports may omit bytes/history: disclose gaps, require exact matching originals where available and never fabricate migrated approvals. The new origin cannot directly read the old origin's browser stores.
>
> FastAPI owns domain rules, authentication, resource access, review/approval guards and transactions. Next.js owns pages/interactions and calls the API through one typed client with generated OpenAPI types; no duplicate workflow backend or direct database writes. PostgreSQL is authoritative. Use server-derived account identity, idempotent commands, exact version/dependency guards and immutable decisions/audit history. Frontend controls or cache freshness cannot authorize a signature.
>
> Provide separate fictional development accounts with server sessions/capabilities, clearly labelled as development identities. Preserve actor responsibilities and independent-review rules. Do not infer clinical criteria, dosing, treatment delivery or institutional qualification. Keep synthetic input fixtures, test-only gold and public research references separate; never join unrelated real subjects into a fictional chart.
>
> Implement every unit in dependency order with working API/React features, committed lockfiles, Alembic migrations, typed contracts and documented local setup. Use the plan's file ownership if delegating; other agents may be working here, so accommodate changes and do not revert them. U12 owns shared layout/navigation/session/query integration; feature units own their domain/UI modules.
>
> Run new backend domain/HTTP tests with real isolated PostgreSQL for concurrency and transaction proof; frontend type/lint/component/build checks; generated-contract checks; and Playwright journeys against the actual API and authenticated development accounts. Use gstack browse for manual browser work. Verify failure recovery, stale signatures, unauthorized requests, originals, amendments, independent impacts, unchanged follow-up and full restoration. Complete the Definition of Done and update the guide; scaffolding or a happy-path screenshot is insufficient.
>
> Institutional SSO/real-user qualification, hospital integration, cohort analytics, prospective-study administration, clinical extraction evaluation and deployment remain separate milestones. Development authentication and a shared backend are part of this build. Report changed files, demonstrated behavior, current verification and remaining limits. Resolve routine implementation choices; raise only essential missing decisions or verified contract conflicts. Passing synthetic tests does not establish clinical validation.

- [Implementation authority, revision 2](2026-10-11-1137-feat-oncology-department-journey-plan.md)
- [Dataset and report-structure guide](../../research_oncology_datasets/dataset-guide.md)
- [Archived vanilla-stack plan](history/2026-10-11-oncology-vanilla-plan.md)
