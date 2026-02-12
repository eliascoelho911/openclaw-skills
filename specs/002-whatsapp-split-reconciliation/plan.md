# Implementation Plan: Reconciliacao Mensal de Compras Compartilhadas

**Branch**: `[002-whatsapp-split-reconciliation]` | **Date**: 2026-02-11 | **Spec**: `/home/elias/workspace/openclaw-skills/specs/002-whatsapp-split-reconciliation/spec.md`
**Input**: Feature specification from `/specs/002-whatsapp-split-reconciliation/spec.md`

## Summary

Implementar uma API REST com FastAPI e persistencia em PostgreSQL para registrar
compras e estornos em modelo append-only, consultar resumo mensal parcial e
gerar relatorio mensal sob demanda, incluindo busca de movimentacoes por filtros
e suporte a estorno vinculado por `original_purchase_external_id`. O desenho
tecnico adota SQLAlchemy 2.x + psycopg para acesso ao banco, Alembic para
migracoes, calculo monetario com `Decimal` (2 casas) e regras de dominio para
deduplicacao e limite de estorno.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x, psycopg 3, Alembic, Typer  
**Storage**: PostgreSQL 16 (movimentacoes append-only e consultas mensais sob demanda)  
**Testing**: pytest (unit, integration, contract), FastAPI TestClient/httpx, testes de carga para validacao de budget  
**Target Platform**: Linux (execucao local com `uv` e deploy em Docker)  
**Project Type**: web API backend (`apps/compras_divididas`)  
**Performance Goals**: registro <=2s p95 (20 lancamentos/min), resumo <=3s (ate 5.000 movimentacoes/mes), relatorio mensal <=5s (ate 5.000 movimentacoes/mes)  
**Constraints**: v1 sem autenticacao; `requested_by` obrigatorio; `occurred_at` opcional com default no registro atual; `payer_participant_id` opcional com default igual a `requested_by`; mes por timezone fixo `America/Sao_Paulo`; arredondamento por movimentacao em 2 casas; proibido editar/excluir; deduplicar por (mes, participante, external_id); estorno deve aceitar vinculo por `original_purchase_id` ou `original_purchase_external_id`; busca de movimentacoes exige competencia mensal no filtro; sem fechamento mensal na v1  
**Scale/Scope**: contexto de 2 participantes ativos; historico consultavel minimo de 24 meses; volume alvo de ate 5.000 movimentacoes por mes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Avaliacao inicial (pre-Fase 0)

- **Code Quality Gate**: PASS - o plano exige `uv run ruff check .`, `uv run ruff format .`, `uv run mypy .` e testes automatizados no escopo alterado.
- **Testing Gate**: PASS - cobertura definida para unit (regras de negocio), integration (persistencia PostgreSQL) e contract (endpoints + codigos HTTP), incluindo regressao para duplicidade e estorno excedente.
- **UX Consistency Gate**: PASS - a API mantera terminologia unica (`compra`, `estorno`, `relatorio`, `saldo`, `transferencia`) e erros com causa + acao esperada.
- **Performance Gate**: PASS - budgets PR-001..PR-003 incorporados com validacao por testes de carga representativos antes do release.
- **Simplicity & Safety Gate**: PASS - abordagem simples (registro append-only + consultas sob demanda), com trilha de auditoria minima e logs estruturados para fluxos criticos.

### Reavaliacao pos-design (pos-Fase 1)

- **Code Quality Gate**: PASS - estrutura por camadas suporta tipagem estrita, lint e manutencao sem duplicacao.
- **Testing Gate**: PASS - `research.md`, `data-model.md`, `contracts/openapi.yaml` e `quickstart.md` detalham matriz de validacao e criterios de regressao.
- **UX Consistency Gate**: PASS - contratos padronizam dinheiro BRL com duas casas e formato de datas consistente em resumo e relatorio mensal.
- **Performance Gate**: PASS - modelo inclui indices por competencia/participante/external_id e agregacoes diretas suficientes para 5.000 movimentacoes por mes.
- **Simplicity & Safety Gate**: PASS - sem violacoes constitucionais; complexidade extra (resolucao por external_id + bloqueio para estorno) e necessaria para FR-004, FR-006A e FR-017.

## Project Structure

### Documentation (this feature)

```text
/home/elias/workspace/openclaw-skills/specs/002-whatsapp-split-reconciliation/
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
/home/elias/workspace/openclaw-skills/apps/compras_divididas/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   └── versions/
├── src/compras_divididas/
│   ├── api/
│   │   ├── app.py
│   │   ├── dependencies.py
│   │   ├── routes/
│   │   └── schemas/
│   ├── domain/
│   ├── services/
│   ├── repositories/
│   ├── db/
│   └── cli.py
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

/home/elias/workspace/openclaw-skills/packages/common/src/shared/
/home/elias/workspace/openclaw-skills/tests/
```

**Structure Decision**: Adotar backend API em `apps/compras_divididas` com
separacao por camadas (`api`, `services`, `repositories`, `db`) para isolar
regras de dominio de detalhes de infraestrutura e manter testes por nivel.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nenhuma | N/A | N/A |
