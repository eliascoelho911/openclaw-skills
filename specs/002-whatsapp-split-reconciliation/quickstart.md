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

## 6) Fluxo funcional minimo com exemplos HTTP

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

Resposta esperada (201):

```json
{
  "id": "7f8b4432-d2d7-47fd-9d55-d6f7cf8b8d4f",
  "type": "purchase",
  "amount": "120.50",
  "description": "Supermercado",
  "occurred_at": "2026-02-10T09:00:00-03:00",
  "competence_month": "2026-02",
  "requested_by_participant_id": "11111111-1111-1111-1111-111111111111",
  "payer_participant_id": "11111111-1111-1111-1111-111111111111",
  "external_id": "wpp-msg-001",
  "original_purchase_id": null,
  "created_at": "2026-02-10T09:00:00-03:00"
}
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

Resposta esperada (201):

```json
{
  "id": "57f1ef3b-c95d-4e35-bde7-e84e2f8b77ce",
  "type": "refund",
  "amount": "20.50",
  "description": "Produto devolvido",
  "occurred_at": "2026-02-10T09:05:00-03:00",
  "competence_month": "2026-02",
  "requested_by_participant_id": "11111111-1111-1111-1111-111111111111",
  "payer_participant_id": "11111111-1111-1111-1111-111111111111",
  "external_id": null,
  "original_purchase_id": "7f8b4432-d2d7-47fd-9d55-d6f7cf8b8d4f",
  "created_at": "2026-02-10T09:05:00-03:00"
}
```

### 6.3 Buscar movimentacoes para localizar purchase_id

```bash
curl "http://localhost:8000/v1/movements?year=2026&month=2&type=purchase&description=Supermercado&amount=120.50"
```

Resposta esperada (200):

```json
{
  "items": [
    {
      "id": "7f8b4432-d2d7-47fd-9d55-d6f7cf8b8d4f",
      "type": "purchase",
      "amount": "120.50",
      "description": "Supermercado",
      "occurred_at": "2026-02-10T09:00:00-03:00",
      "competence_month": "2026-02",
      "payer_participant_id": "11111111-1111-1111-1111-111111111111",
      "requested_by_participant_id": "11111111-1111-1111-1111-111111111111",
      "external_id": "wpp-msg-001",
      "original_purchase_id": null,
      "created_at": "2026-02-10T09:00:00-03:00"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total_items": 1,
  "total_pages": 1
}
```

### 6.4 Consultar resumo do mes

```bash
curl "http://localhost:8000/v1/months/2026/2/summary"
```

Resposta esperada (200):

```json
{
  "competence_month": "2026-02",
  "total_gross": "120.50",
  "total_refunds": "20.50",
  "total_net": "100.00",
  "participants": [
    {
      "participant_id": "11111111-1111-1111-1111-111111111111",
      "paid_total": "100.00",
      "share_due": "50.00",
      "net_balance": "50.00"
    },
    {
      "participant_id": "22222222-2222-2222-2222-222222222222",
      "paid_total": "0.00",
      "share_due": "50.00",
      "net_balance": "-50.00"
    }
  ],
  "transfer": {
    "amount": "50.00",
    "debtor_participant_id": "22222222-2222-2222-2222-222222222222",
    "creditor_participant_id": "11111111-1111-1111-1111-111111111111"
  }
}
```

### 6.5 Consultar relatorio mensal sob demanda

```bash
curl "http://localhost:8000/v1/months/2026/2/report"
```

Resposta esperada (200): mesma estrutura de `summary`, com consolidacao para o
relatorio mensal sob demanda.

### 6.6 Exemplo de erro funcional

Tentativa de estorno sem referencia da compra original:

```bash
curl -X POST "http://localhost:8000/v1/movements" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "refund",
    "amount": "20.50",
    "description": "Produto devolvido",
    "requested_by_participant_id": "11111111-1111-1111-1111-111111111111"
  }'
```

Resposta esperada (400):

```json
{
  "code": "INVALID_REQUEST",
  "message": "Cause: Refund is missing original purchase reference. Action: Provide original_purchase_id or original_purchase_external_id."
}
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
- relatorio mensal <= 5s

Referencia de automacao: `apps/compras_divididas/tests/integration/test_performance_budget.py`.
