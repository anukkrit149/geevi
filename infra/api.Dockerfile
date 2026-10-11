# Development image for the FastAPI service (local demonstration only; not a production image).
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.6.13 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
# The repository layout is preserved so the fixture loader finds /srv/geevi/fixtures.
WORKDIR /srv/geevi/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/.python-version ./
RUN uv sync --frozen --no-dev --no-group fixtures --no-install-project
COPY apps/api/ ./
COPY fixtures/ /srv/geevi/fixtures/
ENV PATH="/srv/geevi/apps/api/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
