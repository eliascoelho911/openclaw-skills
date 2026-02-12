---

description: "Task list for recurring transactions implementation"
---

# Tasks: Transacoes Recorrentes no Compras Divididas

**Input**: Design documents from `/home/elias/workspace/openclaw-skills/specs/001-add-recurring-transactions/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Testes sao obrigatorios para mudancas de comportamento nesta feature (unit, contract, integration e performance).

**Organization**: Tarefas agrupadas por user story para permitir implementacao e validacao independente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependencia direta)
- **[Story]**: mapeia a tarefa para a user story (US1, US2, US3)
- Todas as tarefas incluem caminho de arquivo explicito

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar estrutura de arquivos e base de trabalho para recorrencias.

- [x] T001 Criar esqueletos dos modulos de recorrencia em `apps/compras_divididas/src/compras_divididas/api/routes/recurrences.py`, `apps/compras_divididas/src/compras_divididas/api/schemas/recurrences.py`, `apps/compras_divididas/src/compras_divididas/repositories/recurrence_repository.py`, `apps/compras_divididas/src/compras_divididas/services/recurrence_service.py`, `apps/compras_divididas/src/compras_divididas/services/recurrence_generation_service.py` e `apps/compras_divididas/src/compras_divididas/domain/recurrence_schedule.py`
- [x] T002 [P] Criar arquivos de testes da feature em `apps/compras_divididas/tests/contract/test_create_recurrence.py`, `apps/compras_divididas/tests/contract/test_generate_recurrences.py`, `apps/compras_divididas/tests/contract/test_update_recurrence_status.py`, `apps/compras_divididas/tests/unit/test_recurrence_service.py`, `apps/compras_divididas/tests/unit/test_recurrence_schedule.py` e `apps/compras_divididas/tests/integration/test_recurrence_generation_resume.py`
- [x] T003 [P] Criar arquivos de modelos ORM de recorrencia em `apps/compras_divididas/src/compras_divididas/db/models/recurrence_rule.py`, `apps/compras_divididas/src/compras_divididas/db/models/recurrence_occurrence.py` e `apps/compras_divididas/src/compras_divididas/db/models/recurrence_event.py`
- [x] T004 [P] Criar revisao Alembic inicial da feature em `apps/compras_divididas/alembic/versions/20260211_01_add_recurrence_tables.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura obrigatoria que bloqueia todas as user stories.

**⚠️ CRITICAL**: Nenhuma user story deve iniciar antes da conclusao desta fase.

- [x] T005 Implementar DDL completa (tabelas, enums, constraints e indices) no migration `apps/compras_divididas/alembic/versions/20260211_01_add_recurrence_tables.py`
- [x] T006 Implementar modelos SQLAlchemy e relacionamentos em `apps/compras_divididas/src/compras_divididas/db/models/recurrence_rule.py`, `apps/compras_divididas/src/compras_divididas/db/models/recurrence_occurrence.py` e `apps/compras_divididas/src/compras_divididas/db/models/recurrence_event.py`
- [x] T007 [P] Exportar novos modelos no pacote ORM em `apps/compras_divididas/src/compras_divididas/db/models/__init__.py`
- [x] T008 [P] Adicionar erros de dominio de recorrencia com mensagens acionaveis em ingles em `apps/compras_divididas/src/compras_divididas/domain/errors.py`
- [x] T009 [P] Mapear erros de integridade de recorrencia para payload padrao `{code,message,details}` em `apps/compras_divididas/src/compras_divididas/api/error_handlers.py`
- [x] T010 Implementar operacoes base de repositorio (lookup, lock, ocorrencia idempotente, eventos append-only) em `apps/compras_divididas/src/compras_divididas/repositories/recurrence_repository.py`
- [x] T011 Implementar wiring base de dependencias/roteamento para recorrencia em `apps/compras_divididas/src/compras_divididas/api/dependencies.py` e `apps/compras_divididas/src/compras_divididas/api/routes/__init__.py`
- [x] T012 [P] Implementar utilitarios de calendario/competencia para ajuste de dia invalido em `apps/compras_divididas/src/compras_divididas/domain/recurrence_schedule.py`

**Checkpoint**: Base pronta para desenvolver user stories em incrementos independentes.

---

## Phase 3: User Story 1 - Cadastrar transacao recorrente (Priority: P1) 🎯 MVP

**Goal**: Permitir criar e listar recorrencias mensais ativas com validacoes de negocio.

**Independent Test**: Cadastrar uma recorrencia valida e listar recorrencias ativas confirmando `status=active` e `next_competence_month` coerente.

### Tests for User Story 1

- [ ] T013 [P] [US1] Escrever contract test de `POST /v1/recurrences` (201, 400, 422) em `apps/compras_divididas/tests/contract/test_create_recurrence.py`
- [ ] T014 [P] [US1] Escrever contract test de `GET /v1/recurrences` com filtros/paginacao em `apps/compras_divididas/tests/contract/test_list_recurrences.py`
- [ ] T015 [P] [US1] Escrever unit tests de validacao de cadastro e calculo de `next_competence_month` em `apps/compras_divididas/tests/unit/test_recurrence_service.py`
- [ ] T016 [US1] Escrever integration test de fluxo cadastrar+listar em `apps/compras_divididas/tests/integration/test_recurrence_create_and_list.py`

### Implementation for User Story 1

- [ ] T017 [P] [US1] Implementar schemas de create/list/response de recorrencia em `apps/compras_divididas/src/compras_divididas/api/schemas/recurrences.py`
- [ ] T018 [US1] Implementar queries de criacao/listagem com filtros de status e competencia em `apps/compras_divididas/src/compras_divididas/repositories/recurrence_repository.py`
- [ ] T019 [US1] Implementar casos de uso de criar/listar e evento `recurrence_created` em `apps/compras_divididas/src/compras_divididas/services/recurrence_service.py`
- [ ] T020 [US1] Implementar handlers `POST /v1/recurrences` e `GET /v1/recurrences` em `apps/compras_divididas/src/compras_divididas/api/routes/recurrences.py`
- [ ] T021 [US1] Conectar dependencias e incluir router de recorrencias em `apps/compras_divididas/src/compras_divididas/api/dependencies.py` e `apps/compras_divididas/src/compras_divididas/api/routes/__init__.py`

**Checkpoint**: US1 funcional, testavel isoladamente e pronta para demo de MVP.

---

## Phase 4: User Story 2 - Gerar lancamentos recorrentes por competencia (Priority: P2)

**Goal**: Gerar lancamentos por competencia com idempotencia, retomada segura e auto-geracao opcional em resumo/relatorio.

**Independent Test**: Com recorrencias ativas existentes, executar geracao para uma competencia duas vezes e confirmar ausencia de duplicidades e contadores corretos.

### Tests for User Story 2

- [ ] T022 [P] [US2] Escrever contract test de `POST /v1/months/{year}/{month}/recurrences/generate` com contadores e idempotencia em `apps/compras_divididas/tests/contract/test_generate_recurrences.py`
- [ ] T023 [P] [US2] Atualizar contract tests de `GET /v1/months/{year}/{month}/summary` e `GET /v1/months/{year}/{month}/report` com `auto_generate` em `apps/compras_divididas/tests/contract/test_get_monthly_summary.py` e `apps/compras_divididas/tests/contract/test_get_monthly_report.py`
- [ ] T024 [P] [US2] Escrever unit tests de ajuste de dia (31->28/29) e transicoes de ocorrencia em `apps/compras_divididas/tests/unit/test_recurrence_schedule.py`
- [ ] T025 [US2] Escrever integration test de retomada apos falha parcial sem duplicar lancamentos em `apps/compras_divididas/tests/integration/test_recurrence_generation_resume.py`

### Implementation for User Story 2

- [ ] T026 [US2] Implementar selecao de elegiveis com lock em lote (`FOR UPDATE SKIP LOCKED`) em `apps/compras_divididas/src/compras_divididas/repositories/recurrence_repository.py`
- [ ] T027 [US2] Implementar orquestracao de geracao com contadores `generated/ignored/blocked/failed` em `apps/compras_divididas/src/compras_divididas/services/recurrence_generation_service.py`
- [ ] T028 [US2] Implementar endpoint `POST /v1/months/{year}/{month}/recurrences/generate` em `apps/compras_divididas/src/compras_divididas/api/routes/recurrences.py`
- [ ] T029 [US2] Adicionar query param opcional `auto_generate` nos handlers de resumo/relatorio em `apps/compras_divididas/src/compras_divididas/api/routes/monthly_reports.py`
- [ ] T030 [US2] Integrar pre-geracao idempotente nos servicos mensais em `apps/compras_divididas/src/compras_divididas/services/monthly_summary_service.py` e `apps/compras_divididas/src/compras_divididas/services/monthly_report_service.py`
- [ ] T031 [US2] Atualizar MCP para repassar `auto_generate` em `apps/compras_divididas/src/compras_divididas/mcp/server.py` e cobrir no teste `apps/compras_divididas/tests/unit/test_mcp_server.py`
- [ ] T032 [US2] Atualizar skill MCP com novo parametro em `skills/compras-divididas-mcp/SKILL.md`, `skills/compras-divididas-mcp/references/api_reference.md`, `skills/compras-divididas-mcp/references/response_templates.md` e `skills/compras-divididas-mcp/scripts/render_tool_response.py`

**Checkpoint**: US2 funcional com geracao idempotente, retomada segura e auto-geracao integrada.

---

## Phase 5: User Story 3 - Gerenciar ciclo de vida da recorrencia (Priority: P3)

**Goal**: Permitir editar, pausar, reativar e encerrar recorrencias sem perder historico e preservando regras de vigencia.

**Independent Test**: Alterar status e dados de uma recorrencia apos geracoes anteriores e confirmar que apenas competencias futuras sao impactadas.

### Tests for User Story 3

- [ ] T033 [P] [US3] Escrever contract test de `PATCH /v1/recurrences/{recurrence_id}` cobrindo lock de `start_competence_month` em `apps/compras_divididas/tests/contract/test_update_recurrence.py`
- [ ] T034 [P] [US3] Escrever contract tests de transicoes `/pause`, `/reactivate` e `/end` em `apps/compras_divididas/tests/contract/test_update_recurrence_status.py`
- [ ] T035 [P] [US3] Expandir unit tests de last-write-wins e regras de transicao de estado em `apps/compras_divididas/tests/unit/test_recurrence_service.py`
- [ ] T036 [US3] Escrever integration test de efeito somente em competencias futuras em `apps/compras_divididas/tests/integration/test_recurrence_lifecycle_effective_month.py`

### Implementation for User Story 3

- [ ] T037 [US3] Implementar mutacoes de update/pause/reactivate/end e estado terminal em `apps/compras_divididas/src/compras_divididas/repositories/recurrence_repository.py`
- [ ] T038 [US3] Implementar regras de negocio de ciclo de vida e eventos (`recurrence_updated`, `recurrence_paused`, `recurrence_reactivated`, `recurrence_ended`) em `apps/compras_divididas/src/compras_divididas/services/recurrence_service.py`
- [ ] T039 [US3] Implementar handlers `PATCH /v1/recurrences/{recurrence_id}`, `POST /v1/recurrences/{recurrence_id}/pause`, `POST /v1/recurrences/{recurrence_id}/reactivate` e `POST /v1/recurrences/{recurrence_id}/end` em `apps/compras_divididas/src/compras_divididas/api/routes/recurrences.py`
- [ ] T040 [US3] Expandir schemas de lifecycle/edicao e metadados de recorrencia em `apps/compras_divididas/src/compras_divididas/api/schemas/recurrences.py`

**Checkpoint**: US3 funcional e independente, com manutencao de recorrencia completa.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consolidar performance, regressao e documentacao transversal.

- [ ] T041 [P] Implementar cenario de performance para 1.000 recorrencias elegiveis (PR-002) em `apps/compras_divididas/tests/integration/test_performance_budget.py`
- [ ] T042 [P] Adicionar regressao de `auto_generate=true` em testes de integracao mensais em `apps/compras_divididas/tests/integration/test_monthly_summary.py` e `apps/compras_divididas/tests/integration/test_monthly_report.py`
- [ ] T043 [P] Atualizar guia de uso da app com fluxo de recorrencias em `apps/compras_divididas/README.md`
- [ ] T044 [P] Atualizar contrato OpenAPI final da feature em `specs/001-add-recurring-transactions/contracts/openapi.yaml`
- [ ] T045 Revisar consistencia de mensagens `Cause: ... Action: ...` para recorrencias em `apps/compras_divididas/src/compras_divididas/domain/errors.py` e `apps/compras_divididas/src/compras_divididas/api/error_handlers.py`
- [ ] T046 Estabilizar fixtures compartilhadas para nova suite de recorrencias em `apps/compras_divididas/tests/conftest.py`
- [ ] T047 [P] Atualizar roteiro de validacao manual e MCP da feature em `specs/001-add-recurring-transactions/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) inicia imediatamente
- Foundational (Phase 2) depende de Setup e bloqueia todas as user stories
- User Stories (Phases 3-5) dependem de Foundational concluida
- Polish (Phase 6) depende das user stories selecionadas concluidas

### User Story Dependency Graph

- Ordem recomendada de entrega: **US1 (P1) -> US2 (P2) -> US3 (P3)**
- US2 depende de estruturas de recorrencia criadas na base e reaproveita cadastro de US1 para dados reais
- US3 depende de regras/eventos implementados em US1 e processamento historico de US2

### Within Each User Story

- Escrever testes e validar falha inicial antes da implementacao
- Implementar schemas/modelagem antes dos services
- Implementar services antes dos endpoints
- Concluir a historia com testes verdes antes de iniciar a proxima prioridade

### Parallel Opportunities

- Setup: T002, T003 e T004 podem rodar em paralelo
- Foundational: T007, T008, T009 e T012 podem rodar em paralelo apos T005/T006
- US1: T013, T014 e T015 podem rodar em paralelo
- US2: T022, T023 e T024 podem rodar em paralelo
- US3: T033, T034 e T035 podem rodar em paralelo
- Polish: T041, T042, T043, T044 e T047 podem rodar em paralelo

---

## Parallel Example: User Story 1

```bash
# Testes da US1 em paralelo
Task: "T013 Contract test POST /v1/recurrences"
Task: "T014 Contract test GET /v1/recurrences"
Task: "T015 Unit tests de recurrence_service"

# Implementacao paralela inicial da US1
Task: "T017 Schemas de recorrencia"
Task: "T018 Queries de criacao/listagem no repositorio"
```

## Parallel Example: User Story 2

```bash
# Testes da US2 em paralelo
Task: "T022 Contract test generate"
Task: "T023 Contract tests auto_generate"
Task: "T024 Unit tests recurrence_schedule"

# Faixa paralela de integracoes
Task: "T031 Atualizar MCP server + teste"
Task: "T032 Atualizar skill MCP"
```

## Parallel Example: User Story 3

```bash
# Testes da US3 em paralelo
Task: "T033 Contract test PATCH recurrence"
Task: "T034 Contract tests pause/reactivate/end"
Task: "T035 Unit tests de lifecycle e last-write-wins"

# Implementacao final da US3
Task: "T038 Regras de ciclo de vida no service"
Task: "T040 Schemas de lifecycle"
```

---

## Implementation Strategy

### MVP First (US1)

1. Concluir Phase 1 e Phase 2
2. Entregar Phase 3 (US1)
3. Validar independent test da US1
4. Demonstrar MVP de cadastro/listagem antes de avancar

### Incremental Delivery

1. Base pronta (Phases 1-2)
2. Entregar US1 e validar
3. Entregar US2 e validar idempotencia/retomada
4. Entregar US3 e validar ciclo de vida
5. Finalizar com Phase 6 (performance, regressao, docs)

### Parallel Team Strategy

1. Time inteiro fecha Setup + Foundational
2. Depois, paralelizar por frente:
   - Pessoa A: endpoints/schemas da historia ativa
   - Pessoa B: services/repositorios da historia ativa
   - Pessoa C: testes contract/integration da historia ativa

---

## Notes

- [P] indica tarefas sem conflito de arquivo/dependencia direta
- Labels [US1]/[US2]/[US3] garantem rastreabilidade por historia
- Cada historia possui criterio de teste independente e entregavel isolado
- Erros devem seguir mensagens acionaveis em ingles conforme `Cause: ... Action: ...`
