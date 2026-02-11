# === Stage 1: Builder ===
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copiar arquivos de workspace necessários para resolver dependências
COPY pyproject.toml uv.lock ./
COPY packages/common/pyproject.toml packages/common/pyproject.toml
COPY apps/example/pyproject.toml apps/example/pyproject.toml

# Exportar requirements e instalar com uv pip
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --locked --no-dev --no-emit-workspace -o requirements.txt && \
    uv venv .venv && \
    uv pip install -r requirements.txt --python .venv/bin/python

# Copiar código fonte
COPY packages/common/src packages/common/src
COPY apps/example/src apps/example/src

# Build das wheels dos pacotes workspace
RUN cd packages/common && \
    uv build --wheel -o dist && \
    cd /app/apps/example && \
    uv build --wheel -o dist

# Instalar todas as wheels de uma vez (resolve dependências entre elas)
RUN uv pip install packages/common/dist/*.whl apps/example/dist/*.whl --python /app/.venv/bin/python

# === Stage 2: Runtime ===
FROM python:3.12-slim

RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --create-home app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

USER app
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "example.main"]
