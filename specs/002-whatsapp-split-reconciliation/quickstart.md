# Quickstart - API de Reconciliacao Mensal

Este guia descreve como preparar ambiente local para rodar a API FastAPI com
persistencia PostgreSQL e validar o fluxo principal da feature.

## Pre-requisitos

- Python 3.12+
- `uv` instalado
- Docker e Docker Compose

## 1) Preparar dependencias

```bash
uv sync
```

## 2) Subir PostgreSQL local

```bash
docker-compose up -d db
```

Banco padrao esperado pelo compose:

- host: `localhost`
- port: `5433`
- db: `mydb`
- user: `myuser`
- password: `mypassword`

## 3) Configurar variaveis de ambiente

```bash
export DATABASE_URL="postgresql+psycopg://myuser:mypassword@localhost:5433/mydb"
export APP_TIMEZONE="America/Sao_Paulo"
```

## 4) Aplicar migracoes

```bash
uv run alembic -c apps/compras_divididas/alembic.ini upgrade head
```

## 5) Iniciar API

```bash
uv run uvicorn compras_divididas.api.app:app --app-dir apps/compras_divididas/src --reload --host 0.0.0.0 --port 8000
```

Swagger UI esperado em `http://localhost:8000/docs`.

## 6) Fluxo funcional minimo

### 6.1 Registrar compra

Exemplo minimo: `occurred_at` e `payer_participant_id` omitidos (API aplica
defaults automaticamente).

```bash
curl -X POST "http://localhost:8000/v1/movements" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "purchase",
    "amount": "120.50",
    "description": "Supermercado",
    "requested_by_participant_id": "11111111-1111-1111-1111-111111111111",
    "external_id": "wpp-msg-001"
  }'
```

### 6.2 Registrar estorno

Exemplo usando `original_purchase_external_id` (sem precisar do `purchase_id`).

```bash
curl -X POST "http://localhost:8000/v1/movements" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "refund",
    "amount": "20.50",
    "description": "Produto devolvido",
    "requested_by_participant_id": "11111111-1111-1111-1111-111111111111",
    "original_purchase_external_id": "wpp-msg-001"
  }'
```

### 6.3 Buscar movimentacoes para localizar purchase_id

```bash
curl "http://localhost:8000/v1/movements?year=2026&month=2&type=purchase&description=Supermercado&amount=120.50"
```

### 6.4 Consultar resumo do mes

```bash
curl "http://localhost:8000/v1/months/2026/2/summary"
```

### 6.5 Fechar mes e obter relatorio final

```bash
curl -X POST "http://localhost:8000/v1/months/2026/2/close" \
  -H "Content-Type: application/json" \
  -d '{
    "requested_by_participant_id": "11111111-1111-1111-1111-111111111111"
  }'
```

## 7) Validacao de qualidade antes de merge

```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```

## 8) Validacao de performance (budget)

Executar cenario de carga representativo antes do release para confirmar:

- registro de movimentacao <= 2s p95
- resumo mensal <= 3s
- fechamento mensal <= 5s
