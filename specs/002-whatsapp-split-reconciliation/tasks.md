# Tasks: Reconciliacao Mensal de Compras Compartilhadas

**Input**: Design documents from `/home/elias/workspace/openclaw-skills/specs/002-whatsapp-split-reconciliation/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/openapi.yaml`, `quickstart.md`

**Tests**: Testes sao obrigatorios para mudancas de comportamento neste repositorio (unit, integration e contract).

**Organization**: Tasks agrupadas por user story para permitir entrega e validacao independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode executar em paralelo (arquivos diferentes, sem dependencia direta)
- **[Story]**: User story associada (`[US1]`, `[US2]`, `[US3]`)
- Todas as descricoes incluem caminho de arquivo explicito

## Path Conventions

- App principal: `apps/compras_divididas/src/compras_divididas/`
- Testes da app: `apps/compras_divididas/tests/`
- Contrato OpenAPI: `specs/002-whatsapp-split-reconciliation/contracts/openapi.yaml`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar configuracoes base do projeto para API + PostgreSQL + migracoes.

- [x] T001 Configurar dependencias FastAPI/SQLAlchemy/psycopg/Alembic em `apps/compras_divididas/pyproject.toml`
- [x] T002 Criar configuracao central de ambiente (`DATABASE_URL`, `APP_TIMEZONE`) em `apps/compras_divididas/src/compras_divididas/core/settings.py`
- [x] T003 [P] Criar engine e session factory SQLAlchemy em `apps/compras_divididas/src/compras_divididas/db/session.py`
- [x] T004 [P] Inicializar metadata/base ORM em `apps/compras_divididas/src/compras_divididas/db/base.py`
- [x] T005 Ajustar bootstrap da API para registrar routers v1 em `apps/compras_divididas/src/compras_divididas/api/app.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura de dominio e persistencia bloqueante para todas as historias.

**⚠️ CRITICAL**: Nenhuma historia deve comecar antes desta fase.

- [x] T006 Criar modelo ORM de participante em `apps/compras_divididas/src/compras_divididas/db/models/participant.py`
- [x] T007 [P] Criar modelo ORM de movimentacao financeira append-only em `apps/compras_divididas/src/compras_divididas/db/models/financial_movement.py`
- [x] T008 Criar migration Alembic com tabelas, checks e indice parcial unico de `external_id` em `apps/compras_divididas/alembic/versions/002_create_financial_core.py`
- [x] T009 [P] Implementar utilitario monetario com `Decimal` e `ROUND_HALF_UP` em `apps/compras_divididas/src/compras_divididas/domain/money.py`
- [x] T010 [P] Implementar utilitario de competencia mensal em timezone `America/Sao_Paulo` em `apps/compras_divididas/src/compras_divididas/domain/competence.py`
- [x] T011 [P] Definir hierarquia de excecoes de dominio em `apps/compras_divididas/src/compras_divididas/domain/errors.py`
- [x] T012 Implementar handler global de erros para codigos HTTP de contrato em `apps/compras_divididas/src/compras_divididas/api/error_handlers.py`

**Checkpoint**: Base pronta para implementar historias de usuario de forma independente.

---

## Phase 3: User Story 1 - Registrar compras e estornos (Priority: P1) 🎯 MVP

**Goal**: Permitir registro de compras/estornos com defaults, deduplicacao e vinculo de estorno por ID ou `external_id`.

**Independent Test**: Registrar compra e estorno no mesmo mes e validar persistencia, valores liquidos e erros de validacao sem depender de resumo/relatorio.

### Tests for User Story 1

- [x] T013 [P] [US1] Criar contract test de `POST /v1/movements` (201/400/404/409/422) em `apps/compras_divididas/tests/contract/test_create_movement.py`
- [x] T014 [P] [US1] Criar integration test para fluxo compra->estorno e limite de estorno em `apps/compras_divididas/tests/integration/test_create_movement_flow.py`
- [x] T015 [P] [US1] Criar unit tests de arredondamento, defaults e deduplicacao em `apps/compras_divididas/tests/unit/test_movement_service_create.py`

### Implementation for User Story 1

- [x] T016 [P] [US1] Criar schemas Pydantic de criacao e resposta de movimentacao em `apps/compras_divididas/src/compras_divididas/api/schemas/movements.py`
- [x] T017 [P] [US1] Implementar repositorio de movimentos com lock da compra original e checagem de duplicidade em `apps/compras_divididas/src/compras_divididas/repositories/movement_repository.py`
- [x] T018 [P] [US1] Implementar repositorio de participantes ativos (exatamente dois) em `apps/compras_divididas/src/compras_divididas/repositories/participant_repository.py`
- [x] T019 [US1] Implementar servico de registro append-only com resolucao por `original_purchase_external_id` em `apps/compras_divididas/src/compras_divididas/services/movement_service.py`
- [x] T020 [US1] Implementar endpoint `POST /v1/movements` em `apps/compras_divididas/src/compras_divididas/api/routes/movements.py`
- [x] T021 [US1] Registrar dependencia de sessao e injecao de servicos em `apps/compras_divididas/src/compras_divididas/api/dependencies.py`
- [x] T022 [US1] Adicionar log estruturado `movement_created` e `refund_rejected` em `apps/compras_divididas/src/compras_divididas/services/movement_service.py`
- [x] T023 [US1] Garantir conformidade do contrato com `specs/002-whatsapp-split-reconciliation/contracts/openapi.yaml`

**Checkpoint**: US1 funcional e testavel isoladamente (MVP de registro financeiro).

---

## Phase 4: User Story 2 - Acompanhar saldo mensal parcial (Priority: P2)

**Goal**: Entregar consulta de resumo mensal parcial e busca de movimentacoes por filtros com paginacao.

**Independent Test**: Consultar resumo e listagem de um mes com e sem movimentacoes e validar totais, saldos e pagina.

### Tests for User Story 2

- [x] T024 [P] [US2] Criar contract test de `GET /v1/movements` com filtros obrigatorios/opcionais em `apps/compras_divididas/tests/contract/test_list_movements.py`
- [x] T025 [P] [US2] Criar contract test de `GET /v1/months/{year}/{month}/summary` em `apps/compras_divididas/tests/contract/test_get_monthly_summary.py`
- [x] T026 [P] [US2] Criar integration test de resumo mensal com mes vazio e mes populado em `apps/compras_divididas/tests/integration/test_monthly_summary.py`

### Implementation for User Story 2

- [x] T027 [P] [US2] Criar schemas de resposta para listagem paginada em `apps/compras_divididas/src/compras_divididas/api/schemas/movement_list.py`
- [x] T028 [P] [US2] Criar schemas de resumo mensal e saldo por participante em `apps/compras_divididas/src/compras_divididas/api/schemas/monthly_summary.py`
- [x] T029 [US2] Implementar consulta de movimentos com filtros (`year`,`month`,`type`,`description`,`amount`,`participant_id`,`external_id`) em `apps/compras_divididas/src/compras_divididas/repositories/movement_query_repository.py`
- [x] T030 [US2] Implementar agregacao de resumo mensal parcial e calculo de saldo 50/50 em `apps/compras_divididas/src/compras_divididas/services/monthly_summary_service.py`
- [x] T031 [US2] Implementar endpoint `GET /v1/movements` em `apps/compras_divididas/src/compras_divididas/api/routes/movements.py`
- [x] T032 [US2] Implementar endpoint `GET /v1/months/{year}/{month}/summary` em `apps/compras_divididas/src/compras_divididas/api/routes/monthly_reports.py`

**Checkpoint**: US2 funcional e validada sem depender da geracao de relatorio final.

---

## Phase 5: User Story 3 - Gerar relatorio mensal sob demanda (Priority: P3)

**Goal**: Gerar relatorio mensal com instrucao explicita de transferencia entre os dois participantes.

**Independent Test**: Consultar relatorio de mes conhecido e validar totais consolidados + devedor/credor/valor de transferencia.

### Tests for User Story 3

- [ ] T033 [P] [US3] Criar contract test de `GET /v1/months/{year}/{month}/report` em `apps/compras_divididas/tests/contract/test_get_monthly_report.py`
- [ ] T034 [P] [US3] Criar integration test para relatorio com transferencia e sem transferencia em `apps/compras_divididas/tests/integration/test_monthly_report.py`
- [ ] T035 [P] [US3] Criar unit tests de instrucao de transferencia (saldo positivo/zero) em `apps/compras_divididas/tests/unit/test_transfer_instruction.py`

### Implementation for User Story 3

- [ ] T036 [US3] Implementar servico de relatorio mensal sob demanda reaproveitando agregacoes do resumo em `apps/compras_divididas/src/compras_divididas/services/monthly_report_service.py`
- [ ] T037 [US3] Implementar endpoint `GET /v1/months/{year}/{month}/report` em `apps/compras_divididas/src/compras_divididas/api/routes/monthly_reports.py`
- [ ] T038 [US3] Adicionar log estruturado `monthly_report_generated` com `participant_id`, `competence_month` e `request_id` em `apps/compras_divididas/src/compras_divididas/services/monthly_report_service.py`
- [ ] T039 [US3] Garantir serializacao monetaria BRL com duas casas no relatorio em `apps/compras_divididas/src/compras_divididas/api/schemas/monthly_summary.py`

**Checkpoint**: US3 funcional com instrucao de transferencia e comportamento para mes vazio.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consolidar qualidade, performance e documentacao transversal.

- [ ] T040 [P] Atualizar guia de uso e exemplos HTTP em `specs/002-whatsapp-split-reconciliation/quickstart.md`
- [ ] T041 Executar e ajustar suite de contrato/integracao/unidade em `apps/compras_divididas/tests/`
- [ ] T042 [P] Criar cenario de teste de carga para budgets PR-001..PR-003 em `apps/compras_divididas/tests/integration/test_performance_budget.py`
- [ ] T043 Revisar consistencia de mensagens de erro (causa + acao) em `apps/compras_divididas/src/compras_divididas/domain/errors.py`
- [ ] T044 Executar checklist final (`ruff`, `mypy`, `pytest`) a partir de `pyproject.toml`

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 (Setup) -> sem dependencias
- Phase 2 (Foundational) -> depende da Phase 1 e bloqueia todas as historias
- Phase 3 (US1) -> depende da Phase 2
- Phase 4 (US2) -> depende da Phase 2 e pode iniciar apos US1 para reaproveitar fluxo de dados real
- Phase 5 (US3) -> depende da Phase 4 para reaproveitar agregacao mensal
- Phase 6 (Polish) -> depende das historias concluidas

### User Story Dependency Graph

- US1 (P1) -> base funcional de movimentacoes
- US2 (P2) -> usa movimentacoes da US1 para resumo/listagem
- US3 (P3) -> usa agregacoes da US2 para relatorio sob demanda

### Within Each User Story

- Escrever testes primeiro e validar falha inicial
- Implementar repositorio/modelos antes dos servicos
- Implementar servicos antes de endpoints
- Concluir historia com testes verdes antes da proxima prioridade

### Parallel Opportunities

- Setup: T003 e T004 em paralelo apos T002
- Foundational: T009, T010 e T011 em paralelo apos T008
- US1: T013, T014 e T015 em paralelo; T016, T017 e T018 em paralelo
- US2: T024, T025 e T026 em paralelo; T027 e T028 em paralelo
- US3: T033, T034 e T035 em paralelo

---

## Parallel Example: User Story 1

```bash
# Tests em paralelo
Task: "T013 [US1] Contract test POST /v1/movements"
Task: "T014 [US1] Integration test compra->estorno"
Task: "T015 [US1] Unit tests de regras de registro"

# Implementacao base em paralelo
Task: "T016 [US1] Schemas de movimentacao"
Task: "T017 [US1] Repositorio de movimentos"
Task: "T018 [US1] Repositorio de participantes"
```

## Parallel Example: User Story 2

```bash
# Contratos em paralelo
Task: "T024 [US2] Contract test GET /v1/movements"
Task: "T025 [US2] Contract test GET /v1/months/{year}/{month}/summary"

# Schemas em paralelo
Task: "T027 [US2] Schema de listagem"
Task: "T028 [US2] Schema de resumo mensal"
```

## Parallel Example: User Story 3

```bash
# Testes em paralelo
Task: "T033 [US3] Contract test GET /v1/months/{year}/{month}/report"
Task: "T034 [US3] Integration test de relatorio"
Task: "T035 [US3] Unit test de transferencia"
```

---

## Implementation Strategy

### MVP First (US1)

1. Concluir Phase 1 + Phase 2
2. Entregar Phase 3 (US1) completa
3. Validar criterios independentes da US1
4. Demonstrar MVP de registro de compras/estornos

### Incremental Delivery

1. Base pronta (Phases 1-2)
2. Entregar US1 e validar
3. Entregar US2 e validar
4. Entregar US3 e validar
5. Finalizar com Phase 6 (polish, performance e checklist de qualidade)

### Suggested MVP Scope

- Escopo MVP recomendado: apenas **US1 (Phase 3)**, pois resolve a dor principal de registro confiavel e cria a base para resumo/relatorio.

---

## Notes

- Cada task segue formato checklist obrigatorio: `- [ ] T### [P?] [US?] Descricao com caminho`
- Labels `[US1]`, `[US2]`, `[US3]` aparecem somente nas fases de user story
- Tasks sem story label pertencem a setup, fundacao ou polish
