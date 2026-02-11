# === Stage 1: Builder ===
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy workspace files required to resolve dependencies
COPY pyproject.toml uv.lock ./
COPY packages/common/pyproject.toml packages/common/pyproject.toml
COPY apps/compras_divididas/pyproject.toml apps/compras_divididas/pyproject.toml

# Export requirements and install with uv pip
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --locked --no-dev --no-emit-workspace -o requirements.txt && \
    uv venv .venv && \
    uv pip install -r requirements.txt --python .venv/bin/python

# Copy source code
COPY packages/common/src packages/common/src
COPY apps/compras_divididas/src apps/compras_divididas/src

# Build workspace wheels
RUN cd packages/common && \
    uv build --wheel -o dist && \
    cd /app/apps/compras_divididas && \
    uv build --wheel -o dist

# Install all wheels at once (resolves inter-workspace dependencies)
RUN uv pip install packages/common/dist/*.whl apps/compras_divididas/dist/*.whl --python /app/.venv/bin/python

# === Stage 2: Runtime ===
FROM python:3.12-slim

RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --create-home app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

USER app
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "compras_divididas.cli", "healthcheck"]
