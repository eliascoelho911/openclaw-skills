# compras-divididas

API FastAPI para reconciliacao mensal de compras compartilhadas entre duas pessoas,
com suporte a servidor MCP para uso por clientes LLM.

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker e Docker Compose (opcional, recomendado para Postgres local)

## Instalacao

Execute os comandos a partir da raiz do repositorio:

```bash
uv sync
```

### Banco local (opcional via Docker)

```bash
docker compose up -d db
```

Configure variaveis de ambiente:

```bash
export DATABASE_URL="postgresql+psycopg://myuser:mypassword@localhost:5433/mydb"
export APP_TIMEZONE="America/Sao_Paulo"
```

Rode as migracoes:

```bash
uv run alembic -c apps/compras_divididas/alembic.ini upgrade head
```

## Deploy de producao com Docker

1. Crie o arquivo de ambiente de producao e ajuste os valores:

```bash
cp .env.production.example .env.production
```

2. Suba API + PostgreSQL em modo detached:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

3. Valide a saude da aplicacao:

```bash
curl http://localhost:8000/health/ready
```

4. Para parar:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

Variaveis de runtime usadas pelo container da API:

- `API_PORT` (porta publicada no host via Docker Compose)
- `DATABASE_URL`
- `RUN_DB_MIGRATIONS` (`true`/`false`)
- `API_WORKERS`
- `API_LOG_LEVEL`
- `FORWARDED_ALLOW_IPS`

## Execucao da API

```bash
uv run uvicorn compras_divididas.api.app:app --app-dir apps/compras_divididas/src --host 0.0.0.0 --port 8000 --reload
```

Endpoints principais:

- `GET /health/live`
- `GET /health/ready`
- `GET /v1/participants`
- `GET /v1/movements`
- `POST /v1/movements`
- `GET /v1/recurrences`
- `POST /v1/recurrences`
- `PATCH /v1/recurrences/{recurrence_id}`
- `POST /v1/recurrences/{recurrence_id}/pause`
- `POST /v1/recurrences/{recurrence_id}/reactivate`
- `POST /v1/recurrences/{recurrence_id}/end`
- `POST /v1/months/{year}/{month}/recurrences/generate`
- `GET /v1/months/{year}/{month}/summary`
- `GET /v1/months/{year}/{month}/report`

Swagger: `http://localhost:8000/docs`

## Fluxo de recorrencias (manual)

1. Crie uma recorrencia mensal com `POST /v1/recurrences`.
2. Gere lancamentos da competencia com `POST /v1/months/{year}/{month}/recurrences/generate`.
3. Consulte consolidado mensal com:
   - `GET /v1/months/{year}/{month}/summary?auto_generate=true`
   - `GET /v1/months/{year}/{month}/report?auto_generate=true`
4. Gerencie ciclo de vida com `PATCH`, `pause`, `reactivate` e `end`.

Com `auto_generate=true`, resumo e relatorio executam geracao idempotente antes da
consulta para evitar mes sem lancamentos recorrentes.

## Execucao do servidor MCP

O servidor MCP roda em `stdio` e faz proxy para a API HTTP.

Comando padrao:

```bash
uv run python -m compras_divididas.cli mcp
```

Com override de URL da API e timeout:

```bash
uv run python -m compras_divididas.cli mcp --api-base-url "http://127.0.0.1:8000" --timeout-seconds 10
```

Variaveis opcionais:

- `MCP_API_BASE_URL` (default: `http://127.0.0.1:8000`)
- `MCP_API_TIMEOUT_SECONDS` (default: `10.0`)

## Instalando no cliente MCP

Configure o cliente MCP para iniciar o servidor com `uv`.

### Exemplo - Claude Desktop

Arquivo de configuracao (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "compras-divididas": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "compras_divididas.cli",
        "mcp",
        "--api-base-url",
        "http://127.0.0.1:8000"
      ],
      "cwd": "/home/elias/workspace/openclaw-skills"
    }
  }
}
```

### Exemplo - Cursor (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "compras-divididas": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "compras_divididas.cli",
        "mcp"
      ],
      "cwd": "/home/elias/workspace/openclaw-skills",
      "env": {
        "MCP_API_BASE_URL": "http://127.0.0.1:8000",
        "MCP_API_TIMEOUT_SECONDS": "10"
      }
    }
  }
}
```

Depois de salvar a configuracao:

1. Reinicie o cliente MCP.
2. Verifique se o servidor `compras-divididas` aparece como conectado.
3. Teste uma tool, por exemplo `list_participants`.

## Comandos uteis de qualidade

```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```
