# Development image for the Next.js frontend (local demonstration only; not a production image).
FROM node:24-slim
RUN corepack enable
WORKDIR /srv/geevi
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web/ apps/web/
# The same-origin /api/v1 proxy target is fixed when the app is built.
ARG GEEVI_API_ORIGIN=http://api:8000
ENV GEEVI_API_ORIGIN=$GEEVI_API_ORIGIN NEXT_TELEMETRY_DISABLED=1
RUN pnpm --dir apps/web build
EXPOSE 3000
CMD ["pnpm", "--dir", "apps/web", "exec", "next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
