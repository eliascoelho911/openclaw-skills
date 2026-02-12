# Implementation Plan: Transacoes Recorrentes no Compras Divididas

**Branch**: `[001-add-recurring-transactions]` | **Date**: 2026-02-11 | **Spec**: `/home/elias/workspace/openclaw-skills/specs/001-add-recurring-transactions/spec.md`
**Input**: Feature specification from `/specs/001-add-recurring-transactions/spec.md`

## Summary

Implementar suporte a recorrencias mensais no backend `compras_divididas` com
API para cadastro, listagem, edicao e transicoes de ciclo de vida
(`ativa`/`pausada`/`encerrada`), alem de endpoint de geracao por competencia.
O desenho tecnico adota tres agregados novos (`recurrence_rule`,
`recurrence_occurrence`, `recurrence_event`) para garantir idempotencia por
recorrencia+competencia, rastreabilidade funcional e retomada segura em
reexecucoes apos falha parcial, reutilizando as regras ja consolidadas de
participantes, competencia e criacao de lancamentos.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x, psycopg 3, Alembic, Typer  
**Storage**: PostgreSQL 16 com tabelas novas para recorrencias, ocorrencias e eventos, integradas a `financial_movements` e `participants`  
**Testing**: pytest (unit, integration, contract, performance), FastAPI TestClient/httpx  
**Target Platform**: Linux (execucao local com `uv` e deploy em Docker)  
**Project Type**: web API backend (`apps/compras_divididas`)  
**Performance Goals**: cadastro/edicao/alteracao de status <=2s p95 com 100 usuarios ativos; geracao de ate 1.000 recorrencias elegiveis <=30s com taxa de falha <1%; consulta mensal com ate 2.000 lancamentos <=2s p95  
**Constraints**: recorrencia mensal apenas na v1; sem exclusao fisica (apenas pausar/reativar/encerrar); last-write-wins para edicoes concorrentes; bloquear geracao com dados obrigatorios inconsistentes; impedir alteracao de `start_competence_month` apos primeira geracao; ajustar dia inexistente para ultimo dia valido do mes; mensagens de erro acionaveis e em ingles  
**Scale/Scope**: ate 1.000 recorrencias elegiveis por competencia e historico minimo de 24 meses, mantendo compatibilidade com fluxos atuais de movimentos e consolidacao mensal

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Avaliacao inicial (pre-Fase 0)

- **Code Quality Gate**: PASS - plano define execucao de `uv run ruff check .`,
  `uv run ruff format .`, `uv run mypy .` e testes no escopo alterado antes de
  merge.
- **Testing Gate**: PASS - cobertura prevista para unit (calendario e regras de
  estado), integration (idempotencia/concorrencia com PostgreSQL) e contract
  (endpoints de recorrencia e geracao), incluindo regressao para duplicidade e
  retomada apos interrupcao.
- **UX Consistency Gate**: PASS - terminologia padrao (`recorrencia`,
  `competencia`, `lancamento`) sera mantida em payloads e mensagens; erros
  seguirao padrao `Cause: ... Action: ...`.
- **Performance Gate**: PASS - budgets PR-001..PR-003 incorporados ao plano, com
  validacao por teste automatizado de carga para 1.000 recorrencias elegiveis.
- **Simplicity & Safety Gate**: PASS - complexidade limitada a tres agregados
  novos para suportar auditabilidade e idempotencia; sem mudanca breaking no
  contrato atual de movimentos/resumos.

### Reavaliacao pos-design (pos-Fase 1)

- **Code Quality Gate**: PASS - separacao por camadas (`api`, `services`,
  `repositories`, `db`, `domain`) preserva tipagem estrita e evita duplicacao de
  validacoes ja existentes.
- **Testing Gate**: PASS - artefatos `research.md`, `data-model.md`,
  `contracts/openapi.yaml` e `quickstart.md` especificam matriz completa de
  validacao funcional, regressao e desempenho.
- **UX Consistency Gate**: PASS - contratos padronizam status de recorrencia,
  mensagens acionaveis e diferenciam explicitamente edicao de regra futura versus
  alteracao de lancamento ja gerado.
- **Performance Gate**: PASS - modelo inclui indices para elegibilidade e
  idempotencia (`status+competence`, `unique(recurrence_id, competence_month)`),
  suficientes para o volume alvo com rerun seguro.
- **Simplicity & Safety Gate**: PASS - nenhuma violacao constitucional restante;
  decisoes de lock por competencia e ledger de ocorrencias sao justificadas por
  FR-006, FR-011 e edge case de interrupcao.

## Project Structure

### Documentation (this feature)

```text
/home/elias/workspace/openclaw-skills/specs/001-add-recurring-transactions/
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
├── alembic/
│   └── versions/
├── src/compras_divididas/
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── routes/
│   │   │   ├── movements.py
│   │   │   └── recurrences.py                 # novo
│   │   └── schemas/
│   │       └── recurrences.py                 # novo
│   ├── db/models/
│   │   ├── financial_movement.py
│   │   ├── recurrence_event.py                # novo
│   │   ├── recurrence_occurrence.py           # novo
│   │   └── recurrence_rule.py                 # novo
│   ├── domain/
│   │   └── recurrence_schedule.py             # novo
│   ├── repositories/
│   │   ├── movement_repository.py
│   │   └── recurrence_repository.py           # novo
│   └── services/
│       ├── movement_service.py
│       ├── recurrence_generation_service.py   # novo
│       └── recurrence_service.py              # novo
└── tests/
    ├── contract/
    │   ├── test_create_recurrence.py          # novo
    │   ├── test_generate_recurrences.py       # novo
    │   └── test_update_recurrence_status.py   # novo
    ├── integration/
    │   └── test_recurrence_generation_resume.py # novo
    └── unit/
        ├── test_recurrence_schedule.py        # novo
        └── test_recurrence_service.py         # novo

/home/elias/workspace/openclaw-skills/packages/common/src/shared/
/home/elias/workspace/openclaw-skills/tests/
```

**Structure Decision**: Manter a arquitetura backend existente em
`apps/compras_divididas` e adicionar o modulo de recorrencias nas mesmas camadas
ja adotadas. Essa escolha reduz risco de regressao porque reutiliza validacoes de
participantes/movimentos e concentra novas regras no dominio de recorrencias.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nenhuma | N/A | N/A |
