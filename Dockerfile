## Multi-stage build: builds the Vite SPA, then bundles the FastAPI backend
## with the built assets served at `/`.

# ---- Stage 1: build the frontend ----
FROM node:20-alpine AS frontend-builder
WORKDIR /workspace/frontend

# Clerk publishable key is baked at build time.
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=${VITE_CLERK_PUBLISHABLE_KEY}
# When the SPA is served from the same origin as the backend, leave empty.
ARG VITE_BACKEND_URL=""
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}

COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend runtime ----
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DANOTE_SERVE_FRONTEND=1 \
    DANOTE_FRONTEND_DIST_PATH=/app/backend/static \
    DANOTE_HOST=0.0.0.0 \
    DANOTE_PORT=8000 \
    DANOTE_DB_PATH=/data/danote.sqlite3 \
    DANOTE_GEMINI_CHANGES_LOG_PATH=/data/gemini-applied-changes.jsonl

# System deps (libpython needs libffi; cryptography wheel is pure on slim).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.lock.txt /tmp/requirements.lock.txt
RUN pip install --no-cache-dir -r /tmp/requirements.lock.txt

COPY backend/ /app/backend/
COPY --from=frontend-builder /workspace/frontend/dist /app/backend/static

WORKDIR /app/backend
RUN mkdir -p /data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health > /dev/null || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
