# Data Model - compras-divididas

## Entidades

### 1) Participant

- Purpose: representa uma das duas pessoas do fechamento bilateral.
- Fields:
  - `id` (UUID, PK)
  - `external_id` (TEXT, unique, not null)
  - `display_name` (TEXT, not null)
  - `created_at` (TIMESTAMPTZ, not null)
- Validation Rules:
  - `external_id` deve ser unico no contexto do casal.
  - Fechamento so pode ocorrer com exatamente 2 participantes ativos.

### 2) ProcessRun

- Purpose: registra cada processamento de lote para auditoria e idempotencia.
- Fields:
  - `id` (UUID, PK)
  - `period_year` (INT, not null)
  - `period_month` (INT, not null, 1..12)
  - `input_hash` (TEXT, unique, not null)
  - `source_type` (ENUM: `manual_copy`, `whatsapp_export`)
  - `prompt_version` (TEXT, not null)
  - `schema_version` (TEXT, not null)
  - `status` (ENUM: `received`, `parsed`, `reconciled`, `failed`)
  - `created_at` (TIMESTAMPTZ, not null)
  - `completed_at` (TIMESTAMPTZ, nullable)
- Validation Rules:
  - `input_hash` duplicado para mesmo periodo deve reaproveitar resultado existente.
  - `period_year` e `period_month` obrigatorios para filtragem do fechamento.

### 3) RawMessage

- Purpose: armazena a mensagem original recebida antes da classificacao.
- Fields:
  - `id` (UUID, PK)
  - `run_id` (UUID, FK -> ProcessRun.id, not null)
  - `source_message_id` (TEXT, nullable)
  - `author_external_id` (TEXT, not null)
  - `author_display_name` (TEXT, not null)
  - `content` (TEXT, not null)
  - `sent_at` (TIMESTAMPTZ, nullable)
  - `inferred_month` (BOOLEAN, not null, default `false`)
  - `created_at` (TIMESTAMPTZ, not null)
- Validation Rules:
  - Mensagens sem data podem ser aceitas, mas devem marcar `inferred_month=true`.
  - Mensagens sem autor identificado devem gerar item invalido e nao entram no calculo.

### 4) ExtractedEntry

- Purpose: representa resultado de extracao/classificacao por mensagem.
- Fields:
  - `id` (UUID, PK)
  - `run_id` (UUID, FK -> ProcessRun.id, not null)
  - `raw_message_id` (UUID, FK -> RawMessage.id, not null)
  - `participant_id` (UUID, FK -> Participant.id, nullable)
  - `normalized_description` (TEXT, nullable)
  - `amount_cents` (BIGINT, nullable)
  - `currency` (TEXT, default `BRL`)
  - `classification` (ENUM: `valid`, `invalid`, `ignored`, `deduplicated`)
  - `reason_code` (TEXT, nullable)
  - `reason_message` (TEXT, nullable)
  - `is_refund_keyword` (BOOLEAN, default `false`)
  - `dedupe_key` (TEXT, nullable)
  - `dedupe_bucket_5m` (BIGINT, nullable)
  - `included_in_calculation` (BOOLEAN, not null)
  - `created_at` (TIMESTAMPTZ, not null)
- Validation Rules:
  - `amount_cents` deve ser diferente de zero para classificacao `valid`.
  - Valor negativo so pode ser `valid` quando `is_refund_keyword=true`.
  - `currency` deve ser sempre `BRL`.
  - Dedupe aplica regra: mesmo autor + descricao normalizada + valor + janela de 5 min.

### 5) MonthlyClosure

- Purpose: snapshot consolidado do fechamento mensal para consulta e auditoria.
- Fields:
  - `id` (UUID, PK)
  - `run_id` (UUID, FK -> ProcessRun.id, unique, not null)
  - `period_year` (INT, not null)
  - `period_month` (INT, not null)
  - `participant_a_id` (UUID, FK -> Participant.id, not null)
  - `participant_b_id` (UUID, FK -> Participant.id, not null)
  - `total_a_cents` (BIGINT, not null)
  - `total_b_cents` (BIGINT, not null)
  - `net_balance_cents` (BIGINT, not null)
  - `payer_id` (UUID, FK -> Participant.id, nullable)
  - `receiver_id` (UUID, FK -> Participant.id, nullable)
  - `transfer_amount_cents` (BIGINT, not null)
  - `valid_count` (INT, not null)
  - `invalid_count` (INT, not null)
  - `ignored_count` (INT, not null)
  - `deduplicated_count` (INT, not null)
  - `status` (ENUM: `finalized`, `superseded`)
  - `created_at` (TIMESTAMPTZ, not null)
- Validation Rules:
  - `participant_a_id` deve ser diferente de `participant_b_id`.
  - Quando `transfer_amount_cents=0`, `payer_id` e `receiver_id` podem ser nulos.

### 6) ClosureLineItem

- Purpose: liga cada `ExtractedEntry` ao fechamento para relatorio detalhado.
- Fields:
  - `id` (UUID, PK)
  - `closure_id` (UUID, FK -> MonthlyClosure.id, not null)
  - `entry_id` (UUID, FK -> ExtractedEntry.id, not null)
  - `display_order` (INT, not null)
  - `created_at` (TIMESTAMPTZ, not null)
- Validation Rules:
  - `display_order` deve ser deterministico para manter mesma saida em reexecucoes identicas.

## Relacionamentos

- `ProcessRun` 1:N `RawMessage`
- `ProcessRun` 1:N `ExtractedEntry`
- `RawMessage` 1:1 `ExtractedEntry` (no contexto de uma versao de run)
- `ProcessRun` 1:1 `MonthlyClosure`
- `MonthlyClosure` 1:N `ClosureLineItem`
- `Participant` 1:N `ExtractedEntry` e `MonthlyClosure`

## Regras de validacao derivadas dos requisitos

- FR-013: rejeitar fechamento com mais de 2 participantes.
- FR-014: exibir valores com duas casas decimais e formato BRL.
- FR-015/FR-016: registrar itens deduplicados no relatorio, excluidos do calculo.
- FR-017/FR-018: negativos apenas com palavra-chave explicita de estorno.
- FR-020: sem data identificavel recebe mes atual com flag de inferencia.
- PR-001..PR-003: indices em `(period_year, period_month)`, `(author_external_id, dedupe_bucket_5m)`, `(classification)` para manter latencia alvo.

## Transicoes de estado

### ProcessRun

- `received` -> `parsed` -> `reconciled`
- `received|parsed` -> `failed`

### ExtractedEntry

- `parsed` (estado logico interno) -> `valid`
- `parsed` (estado logico interno) -> `invalid`
- `parsed` (estado logico interno) -> `ignored`
- `valid` -> `deduplicated` (quando regra de janela identifica duplicata)

### MonthlyClosure

- `finalized` -> `superseded` (quando novo reprocessamento substitui fechamento anterior do mesmo periodo)
