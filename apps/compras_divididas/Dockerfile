# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m pip install --upgrade pip

COPY packages/common /build/packages/common
COPY apps/compras_divididas /build/apps/compras_divididas

RUN python -m pip wheel --wheel-dir /wheels /build/packages/common /build/apps/compras_divididas


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /wheels /wheels

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

COPY apps/compras_divididas/alembic /app/apps/compras_divididas/alembic
COPY apps/compras_divididas/alembic.ini /app/apps/compras_divididas/alembic.ini
COPY apps/compras_divididas/scripts/entrypoint.sh /app/apps/compras_divididas/scripts/entrypoint.sh

RUN chmod +x /app/apps/compras_divididas/scripts/entrypoint.sh && \
    chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health/live', timeout=3)" || exit 1

ENTRYPOINT ["/app/apps/compras_divididas/scripts/entrypoint.sh"]
