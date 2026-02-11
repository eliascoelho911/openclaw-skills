# Implementation Plan: compras-divididas

**Branch**: `[001-whatsapp-split-reconciliation]` | **Date**: 2026-02-11 | **Spec**: `/home/elias/workspace/openclaw-skills/specs/001-whatsapp-split-reconciliation/spec.md`
**Input**: Feature specification from `/home/elias/workspace/openclaw-skills/specs/001-whatsapp-split-reconciliation/spec.md` + user input "Aplicacao binario Python + Skill OpenClaw. Aplicacao: compras-divididas. Banco de dados: Postgres. Para inferencia usar LLM com OpenAIClient."

## Summary

Implementar a aplicacao binaria `compras-divididas` e a Skill OpenClaw compartilhando o mesmo nucleo de dominio para processar mensagens do WhatsApp, classificar lancamentos via pipeline hibrido (regras + OpenAIClient), persistir historico completo em PostgreSQL e gerar fechamento mensal bilateral auditavel e deterministico.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: Typer (CLI), Pydantic v2, SQLAlchemy 2.x, psycopg, Alembic, OpenAIClient (OpenAI API)  
**Storage**: PostgreSQL 16 (historico completo, append-only para runs e fechamentos versionados)  
**Testing**: pytest (unit + integration + contract), benchmarks de performance para 100/500/2000 mensagens  
**Target Platform**: Linux x86_64 (execucao local via binario Python e runtime da Skill OpenClaw)  
**Project Type**: single (workspace Python com app CLI binario + adaptador de skill)  
**Performance Goals**: <=10s para 500 mensagens, <=30s para 2000 mensagens, <=5s para reprocessar ate 50 mensagens alteradas  
**Constraints**: reconciliacao estritamente bilateral; BRL com precisao de centavos; dedupe por autor+descricao normalizada+valor em 5 minutos; valor negativo so com palavra-chave de estorno; resultado deterministico para mesma entrada  
**Scale/Scope**: ate 2000 mensagens por fechamento mensal, 2 participantes por run, retencao historica sem expurgo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 (antes de research.md)

- **Code Quality Gate**: PASS - escopo define execucao de `uv run ruff check .`, `uv run ruff format .`, `uv run mypy .` e `uv run pytest` para modulos impactados.
- **Testing Gate**: PASS - cobertura planejada inclui parser, validacoes de negocio, deduplicacao, calculo de saldo, regressao de estorno e integracao com PostgreSQL.
- **UX Consistency Gate**: PASS - manter termos `lancamento`, `saldo`, `fechamento`, `repasse`; resumo executivo antes do detalhamento; erros com causa e proximo passo.
- **Performance Gate**: PASS - metas numericas herdadas da spec (PR-001 a PR-004) com benchmark cronometrado em lotes 100/500/2000.
- **Simplicity & Safety Gate**: PASS - arquitetura hexagonal com nucleo unico e dois adaptadores (CLI + Skill), logs de execucao e versionamento de fechamento para reprocessamentos.

**Resultado do gate pre-research**: PASS

### Post-Phase 1 (apos design e contratos)

- **Code Quality Gate**: PASS - artefatos de design preservam tooling padrao UV/Ruff/MyPy/Pytest e nao introduzem excecoes.
- **Testing Gate**: PASS - `data-model.md`, `contracts/openapi.yaml` e `quickstart.md` descrevem suites unitarias, integracao e contrato.
- **UX Consistency Gate**: PASS - contratos mantem terminologia da spec e layout de resposta prioriza instrucao de repasse.
- **Performance Gate**: PASS - plano de benchmark define datasets, metricas p95 e criterios de aprovacao objetivos.
- **Simplicity & Safety Gate**: PASS - sem complexidade injustificada; trilha de auditoria, constraints de idempotencia e notas de migracao previstas.

**Resultado do gate pos-design**: PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-whatsapp-split-reconciliation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
packages/
└── common/
    └── src/shared/

apps/
├── example/
└── compras_divididas/
    ├── pyproject.toml
    ├── src/compras_divididas/
    │   ├── __init__.py
    │   ├── cli.py
    │   ├── skill.py
    │   ├── domain/
    │   ├── application/
    │   ├── infrastructure/
    │   │   ├── db/
    │   │   ├── llm/
    │   │   └── repositories/
    │   └── reporting/
    └── tests/
        ├── unit/
        ├── integration/
        └── contract/

tests/
└── test_compras_divididas_integration.py
```

**Structure Decision**: manter o workspace multimodulo atual e adicionar um novo app `apps/compras_divididas` com nucleo de dominio reutilizado entre binario e skill, minimizando acoplamento e facilitando testes.

## Complexity Tracking

Nenhuma violacao constitucional identificada nesta fase.
