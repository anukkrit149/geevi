import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import (
    applicability,
    care,
    department,
    dev,
    exceptions,
    follow_up,
    impacts,
    imports,
    patients,
    plans,
    research,
    sessions,
    sources,
    workspaces,
)
from app.core.errors import DomainError, ErrorResponse

log = logging.getLogger("geevi")

ERRORS = {code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 500)}


def create_app() -> FastAPI:
    app = FastAPI(title="Geevi oncology department journey API", version="0.1.0", docs_url="/api/v1/docs",
                  openapi_url="/api/v1/openapi.json",
                  description="Fictional demonstration API. Development identities; not clinically validated.")

    @app.middleware("http")
    async def private_responses(request: Request, call_next):
        request.state.operation_id = str(uuid.uuid4())
        response = await call_next(request)
        # Patient and source responses are never cacheable or shareable.
        response.headers.setdefault("Cache-Control", "no-store, private")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Operation-Id"] = request.state.operation_id
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        log.info("op=%s code=%s status=%s", getattr(request.state, "operation_id", "-"), exc.code, exc.status)
        return JSONResponse(exc.body(), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse({"error": {"code": "validation_failed", "message": "The request could not be validated.",
                                       "target": None, "next_action": "Correct the listed fields and submit again.",
                                       "details": {"fields": fields}}}, status_code=422)

    @app.exception_handler(SQLAlchemyError)
    async def storage_error(request: Request, exc: SQLAlchemyError):
        log.error("op=%s code=storage_failure type=%s", getattr(request.state, "operation_id", "-"), type(exc).__name__)
        return JSONResponse({"error": {"code": "storage_failure", "message": "The change was not saved. Nothing was partially applied.",
                                       "target": None, "next_action": "Retry the same action; the same command id is safe to repeat.",
                                       "details": None}}, status_code=500)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        log.error("op=%s code=unexpected_failure type=%s", getattr(request.state, "operation_id", "-"), type(exc).__name__)
        return JSONResponse({"error": {"code": "unexpected_failure", "message": "The request failed. Nothing was partially applied.",
                                       "target": None, "next_action": "Retry the same action; the same command id is safe to repeat.",
                                       "details": None}}, status_code=500)

    @app.get("/api/v1/health", tags=["health"])
    def health():
        return {"status": "ok"}

    for module in ROUTERS:
        app.include_router(module.router, prefix="/api/v1", responses=ERRORS)
    return app


ROUTERS = [sessions, workspaces, dev, patients, sources, imports, research, department, applicability, exceptions, plans, care, follow_up, impacts]
app = create_app()
