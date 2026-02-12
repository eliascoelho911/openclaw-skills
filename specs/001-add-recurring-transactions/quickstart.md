# Quickstart - Recorrencias Mensais

Este guia descreve como validar o fluxo principal da feature de recorrencias
mensais no `compras_divididas`.

## Pre-requisitos

- Python 3.12+
- `uv` instalado
- Docker e Docker Compose

## 1) Preparar dependencias

```bash
uv sync
```

## 2) Subir banco local

```bash
docker-compose up -d db
```

Valores esperados no ambiente local:

- host: `localhost`
- port: `5433`
- db: `mydb`
- user: `myuser`
- password: `mypassword`

## 3) Configurar ambiente

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

Swagger esperado em `http://localhost:8000/docs`.

## 6) Fluxo funcional minimo

### 6.1 Cadastrar recorrencia

```bash
curl -X POST "http://localhost:8000/v1/recurrences" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Internet residencial",
    "amount": "120.00",
    "payer_participant_id": "elias",
    "requested_by_participant_id": "elias",
    "split_config": {"mode": "equal"},
    "reference_day": 31,
    "start_competence_month": "2026-02"
  }'
```

Resposta esperada (201): recorrencia criada com `status = "active"`.

### 6.2 Listar recorrencias

```bash
curl "http://localhost:8000/v1/recurrences?status=active&limit=50&offset=0"
```

Resposta esperada (200): lista paginada com `next_competence_month` e
`last_processed_competence_month`.

### 6.3 Gerar recorrencias para uma competencia

```bash
curl -X POST "http://localhost:8000/v1/months/2026/2/recurrences/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "requested_by_participant_id": "elias",
    "include_blocked_details": true
  }'
```

Resposta esperada (200): payload com contadores `generated_count`,
`ignored_count`, `blocked_count`, `failed_count`.

### 6.3.1 Consultar resumo/relatorio com auto-geracao

```bash
curl "http://localhost:8000/v1/months/2026/2/summary?auto_generate=true"
curl "http://localhost:8000/v1/months/2026/2/report?auto_generate=true"
```

Com `auto_generate=true`, a API executa geracao idempotente da competencia antes
de montar o payload de consulta.

### 6.4 Pausar recorrencia

```bash
curl -X POST "http://localhost:8000/v1/recurrences/{recurrence_id}/pause" \
  -H "Content-Type: application/json" \
  -d '{
    "requested_by_participant_id": "elias",
    "reason": "Despesa temporariamente suspensa"
  }'
```

Resposta esperada (200): recorrencia retorna com `status = "paused"`.

### 6.5 Reativar recorrencia

```bash
curl -X POST "http://localhost:8000/v1/recurrences/{recurrence_id}/reactivate" \
  -H "Content-Type: application/json" \
  -d '{"requested_by_participant_id": "elias"}'
```

Resposta esperada (200): recorrencia retorna com `status = "active"`.

### 6.6 Editar recorrencia

```bash
curl -X PATCH "http://localhost:8000/v1/recurrences/{recurrence_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "requested_by_participant_id": "elias",
    "description": "Internet fibra",
    "amount": "139.90"
  }'
```

Resposta esperada (200): apenas competencias futuras ainda nao geradas refletem
os novos valores.

### 6.7 Encerrar recorrencia

```bash
curl -X POST "http://localhost:8000/v1/recurrences/{recurrence_id}/end" \
  -H "Content-Type: application/json" \
  -d '{
    "requested_by_participant_id": "elias",
    "end_competence_month": "2026-12"
  }'
```

Resposta esperada (200): recorrencia retorna com `status = "ended"`.

## 7) Exemplo de erro funcional

Tentativa de mudar `start_competence_month` apos primeira geracao:

```bash
curl -X PATCH "http://localhost:8000/v1/recurrences/{recurrence_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "requested_by_participant_id": "elias",
    "start_competence_month": "2026-01"
  }'
```

Resposta esperada (422):

```json
{
  "code": "START_COMPETENCE_LOCKED",
  "message": "Cause: start_competence_month cannot change after first generation. Action: keep current start_competence_month and edit other fields.",
  "details": {
    "recurrence_id": "9adf8b87-9f52-4f4e-a658-b31f0a589b46"
  }
}
```

## 8) Validacao de qualidade

```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```

## 9) Validacao de performance

Executar o teste de budget da suite para confirmar os limites da feature:

```bash
uv run pytest apps/compras_divididas/tests/integration/test_performance_budget.py
```

Resultados esperados:

- cadastro/edicao/alteracao de status <=2s p95
- geracao de 1.000 recorrencias <=30s
- consulta mensal com 2.000 lancamentos <=2s p95

## 10) Validacao MCP/Skill

Validar a camada MCP/skill com o servidor em execucao:

```bash
uv run python -m compras_divididas.cli mcp
```

Checklist:

1. Chamar `get_monthly_summary` com `auto_generate=true` e confirmar que o
   resumo inclui lancamentos recorrentes do mes.
2. Chamar `get_monthly_report` com `auto_generate=true` e confirmar o mesmo
   comportamento idempotente.
3. Confirmar que `skills/compras-divididas-mcp/SKILL.md` e referencias descrevem
   o parametro opcional e exemplos de uso.
4. Executar teste unitario do MCP para repasse de query param:

```bash
uv run pytest apps/compras_divididas/tests/unit/test_mcp_server.py
```
