# Tasks: compras-divididas

**Input**: Design documents from `/specs/001-whatsapp-split-reconciliation/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/openapi.yaml`, `quickstart.md`

**Tests**: Testes sao obrigatorios para mudancas de comportamento nesta feature (unitarios, integracao, contrato e performance).

**Organization**: Tasks agrupadas por user story para permitir implementacao e validacao independente por incremento.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode ser executada em paralelo (arquivos diferentes, sem dependencia incompleta)
- **[Story]**: Mapeia a task para a user story (`[US1]`, `[US2]`, `[US3]`)
- Todas as tasks incluem caminho de arquivo explicito

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicializar app `compras_divididas` no workspace e pontos de entrada CLI/Skill.

- [x] T001 Criar manifesto do app em `apps/compras_divididas/pyproject.toml`
- [x] T002 Registrar novo app no workspace em `pyproject.toml`
- [x] T003 [P] Atualizar `mypy_path` para o app em `mypy.ini`
- [x] T004 [P] Criar pacote base do app em `apps/compras_divididas/src/compras_divididas/__init__.py`
- [x] T005 [P] Criar bootstrap inicial do CLI Typer em `apps/compras_divididas/src/compras_divididas/cli.py`
- [x] T006 [P] Criar bootstrap inicial da Skill OpenClaw em `apps/compras_divididas/src/compras_divididas/skill.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura obrigatoria antes das user stories (DB, configuracao, portas e adaptadores base).

**⚠️ CRITICAL**: Nenhuma implementacao de user story deve iniciar antes do fim desta fase.

- [x] T007 Implementar carregamento tipado de configuracoes em `apps/compras_divididas/src/compras_divididas/infrastructure/settings.py`
- [x] T008 [P] Implementar engine/sessao SQLAlchemy em `apps/compras_divididas/src/compras_divididas/infrastructure/db/session.py`
- [x] T009 Configurar ambiente Alembic em `apps/compras_divididas/alembic/env.py`
- [x] T010 Criar migracao inicial de tabelas centrais em `apps/compras_divididas/alembic/versions/001_initial_core_tables.py`
- [x] T011 [P] Implementar value objects de dinheiro BRL e periodo em `apps/compras_divididas/src/compras_divididas/domain/value_objects.py`
- [x] T012 [P] Definir portas de repositorio do nucleo em `apps/compras_divididas/src/compras_divididas/application/ports/repositories.py`
- [x] T013 [P] Implementar adaptador OpenAIClient com JSON Schema estrito em `apps/compras_divididas/src/compras_divididas/infrastructure/llm/openai_classifier.py`

**Checkpoint**: Base pronta para implementar historias de usuario.

---

## Phase 3: User Story 1 - Fechar o mes automaticamente (Priority: P1) 🎯 MVP

**Goal**: Consolidar lancamentos validos do mes e retornar instrucao de repasse bilateral com totais e saldo final.

**Independent Test**: Processar um lote mensal valido e validar pagador/recebedor/valor final, incluindo cenarios com apenas um participante e sem lancamentos validos.

### Tests for User Story 1

- [x] T014 [P] [US1] Criar teste de contrato do POST `/v1/monthly-closures` em `apps/compras_divididas/tests/contract/test_create_monthly_closure.py`
- [x] T015 [P] [US1] Criar teste de integracao do fechamento mensal feliz em `apps/compras_divididas/tests/integration/test_close_month_happy_path.py`
- [x] T016 [P] [US1] Criar testes unitarios de calculo bilateral de saldo em `apps/compras_divididas/tests/unit/test_settlement_service.py`

### Implementation for User Story 1

- [x] T017 [P] [US1] Criar modelo ORM de fechamento mensal em `apps/compras_divididas/src/compras_divididas/infrastructure/db/models/monthly_closure.py`
- [x] T018 [P] [US1] Implementar repositorio de fechamento mensal em `apps/compras_divididas/src/compras_divididas/infrastructure/repositories/monthly_closure_repository.py`
- [x] T019 [US1] Implementar caso de uso de fechamento do mes em `apps/compras_divididas/src/compras_divididas/application/use_cases/close_month.py`
- [x] T020 [US1] Expor comando `close-month` no CLI em `apps/compras_divididas/src/compras_divididas/cli.py`
- [x] T021 [US1] Implementar handler POST de fechamento mensal em `apps/compras_divididas/src/compras_divididas/api/monthly_closures.py`

**Checkpoint**: US1 funcional e validavel isoladamente (MVP).

---

## Phase 4: User Story 2 - Interpretar mensagens do WhatsApp com seguranca (Priority: P2)

**Goal**: Classificar mensagens em validas, invalidas e ignoradas com pipeline hibrido (regras + LLM), aplicando estorno e dedupe.

**Independent Test**: Processar lote misto e confirmar classificacao correta por item, incluindo rejeicoes com motivo explicito e deduplicacao na janela de 5 minutos.

### Tests for User Story 2

- [x] T022 [P] [US2] Criar testes unitarios de extracao e normalizacao monetaria em `apps/compras_divididas/tests/unit/test_message_parser.py`
- [x] T023 [P] [US2] Criar testes unitarios de regras de estorno/negativos em `apps/compras_divididas/tests/unit/test_refund_rules.py`
- [x] T024 [P] [US2] Criar teste de integracao do pipeline de classificacao em lote misto em `apps/compras_divididas/tests/integration/test_classification_pipeline.py`

### Implementation for User Story 2

- [x] T025 [P] [US2] Criar modelo ORM de entrada extraida em `apps/compras_divididas/src/compras_divididas/infrastructure/db/models/extracted_entry.py`
- [x] T026 [P] [US2] Definir schemas e enums de classificacao em `apps/compras_divididas/src/compras_divididas/application/schemas/classification.py`
- [x] T027 [US2] Implementar classificador hibrido (regras + OpenAIClient) em `apps/compras_divididas/src/compras_divididas/application/services/message_classifier.py`
- [x] T028 [US2] Implementar regras de dedupe e validacao de estorno em `apps/compras_divididas/src/compras_divididas/domain/services/reconciliation_rules.py`
- [x] T029 [US2] Persistir resultados de classificacao por mensagem em `apps/compras_divididas/src/compras_divididas/infrastructure/repositories/extracted_entry_repository.py`
- [x] T030 [US2] Integrar pipeline de classificacao ao fechamento mensal em `apps/compras_divididas/src/compras_divididas/application/use_cases/close_month.py`

**Checkpoint**: US2 funcional e validavel isoladamente sobre lote misto.

---

## Phase 5: User Story 3 - Conferir o fechamento com transparencia (Priority: P3)

**Goal**: Entregar relatorio detalhado auditavel com validos, rejeitados, deduplicados e consultas historicas de fechamento.

**Independent Test**: Gerar fechamento com itens validos/invalidos/deduplicados e validar consulta detalhada por `closure_id` e por periodo mais recente.

### Tests for User Story 3

- [x] T031 [P] [US3] Criar teste de contrato do GET `/v1/monthly-closures/{closure_id}` em `apps/compras_divididas/tests/contract/test_get_monthly_closure_by_id.py`
- [x] T032 [P] [US3] Criar teste de contrato do GET `/v1/monthly-closures/{year}/{month}/latest` em `apps/compras_divididas/tests/contract/test_get_latest_monthly_closure.py`
- [x] T033 [P] [US3] Criar teste de integracao do relatorio detalhado com rejeitados/deduplicados em `apps/compras_divididas/tests/integration/test_detailed_report.py`

### Implementation for User Story 3

- [x] T034 [P] [US3] Criar modelo ORM de itens do fechamento em `apps/compras_divididas/src/compras_divididas/infrastructure/db/models/closure_line_item.py`
- [x] T035 [US3] Implementar montador de relatorio detalhado em `apps/compras_divididas/src/compras_divididas/reporting/monthly_closure_report.py`
- [x] T036 [US3] Implementar casos de uso de consulta por id e ultimo fechamento do periodo em `apps/compras_divididas/src/compras_divididas/application/use_cases/get_monthly_closure.py`
- [x] T037 [US3] Implementar handlers GET de consulta de fechamento em `apps/compras_divididas/src/compras_divididas/api/monthly_closures.py`
- [x] T038 [US3] Ajustar resposta da Skill com resumo executivo seguido de detalhamento em `apps/compras_divididas/src/compras_divididas/skill.py`

**Checkpoint**: US3 funcional com trilha auditavel e consultas historicas.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Fechamentos de qualidade, performance e documentacao transversal.

- [x] T039 [P] Criar dataset golden deterministico para regressao em `apps/compras_divididas/tests/fixtures/golden/monthly_closure_dataset.json`
- [x] T040 Implementar benchmarks D100/D500/D2000/reprocess_50 em `apps/compras_divididas/tests/performance/test_reconciliation_benchmarks.py`
- [x] T041 [P] Criar regressao ponta-a-ponta de paridade CLI vs Skill em `tests/test_compras_divididas_integration.py`
- [x] T042 Atualizar fluxo executavel e criterios de validacao em `specs/001-whatsapp-split-reconciliation/quickstart.md`
- [x] T043 [P] Documentar arquitetura e operacao do app em `apps/compras_divididas/README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) -> Foundational (Phase 2) -> US1 (Phase 3) -> US2 (Phase 4) -> US3 (Phase 5) -> Polish (Phase 6)

### User Story Dependency Graph

- `US1 (P1)` e a base de entrega de valor (MVP)
- `US2 (P2)` estende o pipeline de entrada do `US1` com classificacao robusta
- `US3 (P3)` depende dos artefatos de fechamento/classificacao de `US1` + `US2` para auditoria completa

Representacao textual: `US1 -> US2 -> US3`

### Parallel Opportunities

- Setup: `T003`, `T004`, `T005`, `T006` podem rodar em paralelo apos `T001`/`T002`
- Foundational: `T008`, `T011`, `T012`, `T013` podem rodar em paralelo apos `T007`
- US1: `T014`, `T015`, `T016` em paralelo; `T017` e `T018` em paralelo antes de `T019`
- US2: `T022`, `T023`, `T024` em paralelo; `T025` e `T026` em paralelo antes de `T027`
- US3: `T031`, `T032`, `T033` em paralelo; `T034` em paralelo com inicio de `T035` quando contratos estiverem estaveis
- Polish: `T039`, `T041`, `T043` em paralelo

---

## Parallel Example: User Story 1

```bash
# Testes US1 em paralelo
Task: "T014 [US1] apps/compras_divididas/tests/contract/test_create_monthly_closure.py"
Task: "T015 [US1] apps/compras_divididas/tests/integration/test_close_month_happy_path.py"
Task: "T016 [US1] apps/compras_divididas/tests/unit/test_settlement_service.py"

# Modelagem/repositorio US1 em paralelo
Task: "T017 [US1] apps/compras_divididas/src/compras_divididas/infrastructure/db/models/monthly_closure.py"
Task: "T018 [US1] apps/compras_divididas/src/compras_divididas/infrastructure/repositories/monthly_closure_repository.py"
```

## Parallel Example: User Story 2

```bash
# Testes US2 em paralelo
Task: "T022 [US2] apps/compras_divididas/tests/unit/test_message_parser.py"
Task: "T023 [US2] apps/compras_divididas/tests/unit/test_refund_rules.py"
Task: "T024 [US2] apps/compras_divididas/tests/integration/test_classification_pipeline.py"

# Base de classificacao US2 em paralelo
Task: "T025 [US2] apps/compras_divididas/src/compras_divididas/infrastructure/db/models/extracted_entry.py"
Task: "T026 [US2] apps/compras_divididas/src/compras_divididas/application/schemas/classification.py"
```

## Parallel Example: User Story 3

```bash
# Contratos/Integracao US3 em paralelo
Task: "T031 [US3] apps/compras_divididas/tests/contract/test_get_monthly_closure_by_id.py"
Task: "T032 [US3] apps/compras_divididas/tests/contract/test_get_latest_monthly_closure.py"
Task: "T033 [US3] apps/compras_divididas/tests/integration/test_detailed_report.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Completar Phase 1 (Setup)
2. Completar Phase 2 (Foundational)
3. Completar Phase 3 (US1)
4. Validar criterios independentes da US1 antes de avancar

### Incremental Delivery

1. Base pronta (Phase 1 + 2)
2. Entregar US1 e validar
3. Entregar US2 e validar lote misto
4. Entregar US3 e validar auditoria/historico
5. Finalizar com Phase 6 (performance, regressao, docs)

### Suggested MVP Scope

- Implementar somente `US1` (T014-T021) apos base (T001-T013), com demonstracao via CLI e endpoint POST.

---

## Notes

- Tasks com `[P]` evitam conflito de arquivo e podem ser distribuidas em paralelo.
- Cada user story permanece testavel de forma independente com seus proprios cenarios.
- Ordem de implementacao interna por story: testes -> modelos/contratos -> servicos/use cases -> handlers/adapters.
