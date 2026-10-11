# Geevi — oncology department journey (fictional demonstration)

A new full-stack application: **Next.js App Router / React / TypeScript** frontend, **FastAPI / Pydantic** backend,
**PostgreSQL** with SQLAlchemy, Psycopg and Alembic. It implements
[the implementation plan](docs/plans/2026-10-11-1137-feat-oncology-department-journey-plan.md) (revision 2, units U1–U14).

> Everything here is fictional. Accounts are development identities, signatures are demonstration records, and no
> clinical content is validated. Passing synthetic tests does not establish clinical validity.

| Path | What it is |
|---|---|
| `apps/api/` | FastAPI service: domain rules, sessions, guards, transactions, Alembic migrations, pytest suite |
| `apps/web/` | Next.js app: pages and interactions only; one typed client generated from the API's OpenAPI |
| `contracts/openapi.json` | Generated API contract (`pnpm contracts:generate` / `pnpm contracts:check`) |
| `fixtures/department-journey/` | Fictional inputs, test-only gold, scenario text, separate public references |
| `scripts/` | Dev database, contract generation/check, browser-test API launcher |
| `infra/`, `compose.yaml` | Development Dockerfiles, environment example, local Compose stack |
| `docs/` | [Development setup](docs/development.md) · [Journey guide, evidence and limits](docs/department-journey-guide.md) |

Quick start: see [docs/development.md](docs/development.md).
Hosting: see [docs/deployment.md](docs/deployment.md). Next.js and FastAPI deploy together using Vercel Services,
with a dedicated Neon PostgreSQL database. The hosted app is a password-protected fictional demonstration.

The legacy vanilla prototype in `../product/` is a read-only reference. Nothing here imports it, reads its browser
storage, or modifies it.
