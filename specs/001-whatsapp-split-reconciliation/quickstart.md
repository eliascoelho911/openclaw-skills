# Quickstart - compras-divididas

Este guia descreve o fluxo alvo para executar localmente a feature apos a implementacao.

## 1) Pre-requisitos

- Python 3.12+
- `uv` instalado
- Docker e Docker Compose
- Chave de API OpenAI (`OPENAI_API_KEY`)

## 2) Preparar ambiente

```bash
uv sync
docker-compose up -d db
```

Defina variaveis de ambiente:

```bash
export DATABASE_URL="postgresql://myuser:mypassword@localhost:5432/mydb"
export OPENAI_API_KEY="<seu-token>"
export OPENAI_MODEL="gpt-4.1-mini"
```

## 3) Aplicar migracoes (quando disponiveis)

```bash
uv run alembic upgrade head
```

## 4) Executar fechamento mensal via CLI binario

Entrada de exemplo (`examples/feb-2026.json`):

```json
{
  "period": { "year": 2026, "month": 2 },
  "participants": [
    { "external_id": "elias", "display_name": "Elias" },
    { "external_id": "esposa", "display_name": "Esposa" }
  ],
  "messages": [
    {
      "message_id": "m1",
      "author_external_id": "elias",
      "author_display_name": "Elias",
      "content": "Mercado R$20",
      "sent_at": "2026-02-05T19:10:00-03:00"
    },
    {
      "message_id": "m2",
      "author_external_id": "esposa",
      "author_display_name": "Esposa",
      "content": "Farmacia R$35,50",
      "sent_at": "2026-02-06T12:35:00-03:00"
    }
  ],
  "reprocess_mode": "new_version"
}
```

Comando alvo:

```bash
uv run python -m compras_divididas.cli close-month --input examples/feb-2026.json
```

Saida esperada (resumo):

```text
Fechamento 2026-02
Pagador: elias
Recebedor: esposa
Valor: R$ 15,50
Validos: 2 | Invalidos: 0 | Ignorados: 0 | Deduplicados: 0
```

## 5) Executar via Skill OpenClaw

Comando alvo da Skill:

```text
/compras-divididas fechar --periodo 2026-02 --arquivo examples/feb-2026.json
```

A Skill deve retornar o mesmo resumo executivo e o detalhamento completo do fechamento.

## 6) Validar qualidade

```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```

## 7) Validar performance (PR-001..PR-004)

```bash
uv run pytest apps/compras_divididas/tests/performance -k "d100 or d500 or d2000 or reprocess_50"
```

Criterios de aprovacao:

- D500: <= 10s (p95)
- D2000: <= 30s (p95)
- Reprocessamento de 50 alteracoes: <= 5s (p95)

## 8) Gerar binario local

```bash
uv run pyinstaller apps/compras_divididas/src/compras_divididas/cli.py --onefile --name compras-divididas
```

Binario esperado em `dist/compras-divididas`.
