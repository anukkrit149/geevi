# Framework reference check

11 October 2026. Official documentation was inspected through the user's gstack browse workflow before the architecture revision. These are mechanics checks, not application test results or evidence that new dependencies are installed.

- [Next.js server and client components](https://nextjs.org/docs/app/getting-started/server-and-client-components): the App Router supports server-rendered structure and client interaction boundaries. The plan assigns the shared shell to Next.js and interactive clinical workflows/source viewing to React client components. FastAPI remains the workflow authority; this boundary is a design decision.
- [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/): framework security tooling supports authentication dependencies. The plan chooses opaque development sessions and explicit capability/resource guards; it does not assume an example authentication mechanism supplies institutional authorization.
- [SQLAlchemy transactions](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html): the documented session transaction boundary commits successful work and rolls back failures. The plan puts version checks, domain decisions, audit and idempotency receipts inside one boundary.
- [PostgreSQL explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html): row locks coordinate conflicting writers until transaction end. The plan chooses one workspace write lock for the small demonstration, with per-entity revisions and scoped dependency checks. Tests must use real PostgreSQL to verify this behavior.

- [TanStack Query focus refetching](https://tanstack.com/query/latest/docs/framework/react/guides/window-focus-refetching): documented focus revalidation supports refreshing frontend projections. Server transaction checks remain authoritative regardless of client freshness.

Versions remain an implementation bootstrap check. The coding agent must select mutually compatible supported versions, pin them in manifests/lockfiles and record the tested runtimes. No old vanilla dependency or test result is claimed as a new-stack baseline.
