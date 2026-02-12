# Data Model - Transacoes Recorrentes

## Visao geral

O modelo adiciona suporte a recorrencias sem quebrar o fluxo append-only ja
existente de `financial_movements`.

Objetivos principais:

1. Guardar a regra de recorrencia editavel para geracoes futuras.
2. Garantir idempotencia por recorrencia e competencia.
3. Preservar historico de eventos funcionais para auditoria.

## Entidades

### 1) RecurrenceRule

Representa a configuracao ativa de uma recorrencia mensal.

| Campo | Tipo | Regra |
|-------|------|-------|
| id | UUID | PK |
| description | VARCHAR(280) | NOT NULL, trim, minimo 1 caractere |
| amount | NUMERIC(12,2) | NOT NULL, `> 0` |
| payer_participant_id | VARCHAR(32) | FK -> `participants.id`, NOT NULL |
| requested_by_participant_id | VARCHAR(32) | FK -> `participants.id`, NOT NULL |
| split_config | JSONB | NOT NULL (v1: `{"mode": "equal"}`) |
| periodicity | ENUM(`monthly`) | NOT NULL |
| reference_day | SMALLINT | NOT NULL, entre 1 e 31 |
| start_competence_month | DATE | NOT NULL, sempre primeiro dia do mes |
| end_competence_month | DATE | NULL, primeiro dia do mes, `>= start` quando informado |
| status | ENUM(`active`,`paused`,`ended`) | NOT NULL |
| first_generated_competence_month | DATE | NULL |
| last_generated_competence_month | DATE | NULL |
| next_competence_month | DATE | NOT NULL, primeiro dia do mes |
| version | INTEGER | NOT NULL, default `1` |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Regras de validacao**

- `amount` deve ser decimal positivo com duas casas.
- `reference_day` fora de 1..31 deve falhar.
- `end_competence_month` nao pode ser anterior a `start_competence_month`.
- Apos primeira geracao, `start_competence_month` torna-se imutavel.
- Exclusao nao e permitida; descontinuacao ocorre por `paused` ou `ended`.
- Edicoes concorrentes usam last-write-wins.

### 2) RecurrenceOccurrence

Ledger de processamento por competencia (uma linha por recorrencia+mes).

| Campo | Tipo | Regra |
|-------|------|-------|
| id | UUID | PK |
| recurrence_rule_id | UUID | FK -> `recurrence_rules.id`, NOT NULL |
| competence_month | DATE | NOT NULL, primeiro dia do mes |
| scheduled_date | DATE | NOT NULL, dia ajustado da competencia |
| status | ENUM(`pending`,`generated`,`blocked`,`failed`) | NOT NULL |
| movement_id | UUID | FK -> `financial_movements.id`, NULL |
| blocked_reason_code | VARCHAR(64) | NULL |
| blocked_reason_message | TEXT | NULL |
| failure_reason | TEXT | NULL |
| attempt_count | INTEGER | NOT NULL, default `0` |
| processed_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Indices e constraints**

- `UNIQUE(recurrence_rule_id, competence_month)` para idempotencia.
- `UNIQUE(movement_id)` parcial (`movement_id IS NOT NULL`) para evitar vinculo
  duplo do mesmo lancamento.
- Indice por `(competence_month, status)` para monitoramento e rerun.

**Regras de validacao**

- Uma ocorrencia por recorrencia+competencia no maximo.
- `movement_id` obrigatorio quando `status = generated`.
- `blocked_reason_code/message` obrigatorios quando `status = blocked`.
- `attempt_count` incrementa a cada tentativa de processamento.

### 3) RecurrenceEvent

Registro append-only de eventos funcionais para auditoria.

| Campo | Tipo | Regra |
|-------|------|-------|
| id | UUID | PK |
| recurrence_rule_id | UUID | FK -> `recurrence_rules.id`, NOT NULL |
| recurrence_occurrence_id | UUID | FK -> `recurrence_occurrences.id`, NULL |
| event_type | ENUM | NOT NULL |
| actor_participant_id | VARCHAR(32) | FK -> `participants.id`, NULL quando acao automatica |
| payload | JSONB | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

`event_type` previstos:

- `recurrence_created`
- `recurrence_updated`
- `recurrence_paused`
- `recurrence_reactivated`
- `recurrence_ended`
- `recurrence_generated`
- `recurrence_blocked`
- `recurrence_failed`
- `recurrence_ignored`

### 4) FinancialMovement (existente, relacao)

`financial_movements` continua append-only. Cada movimento gerado por recorrencia
e vinculado via `recurrence_occurrences.movement_id`, sem alterar retroativamente
movimentos anteriores.

## Relacionamentos

- `participants (1) -> (N) recurrence_rules` por `payer_participant_id`.
- `participants (1) -> (N) recurrence_rules` por `requested_by_participant_id`.
- `recurrence_rules (1) -> (N) recurrence_occurrences`.
- `recurrence_rules (1) -> (N) recurrence_events`.
- `recurrence_occurrences (0..1) -> (1) financial_movements` quando gerado.

## Estados e transicoes

### Ciclo de vida da recorrencia

- Estados: `active`, `paused`, `ended`.
- Transicoes permitidas:
  - `active -> paused`
  - `paused -> active`
  - `active -> ended`
  - `paused -> ended`
- `ended` e terminal.

### Ciclo de processamento da ocorrencia

- Estado inicial: `pending`.
- Transicoes:
  - `pending -> generated`
  - `pending -> blocked`
  - `pending -> failed`
  - `failed -> pending` (retentativa controlada)

## Regras de calendario

- Competencia sempre representa o primeiro dia do mes.
- Data agendada da ocorrencia usa:
  - `scheduled_day = min(reference_day, ultimo_dia_da_competencia)`.
- Exemplo: `reference_day = 31` em fevereiro resulta em dia 28/29.

## Invariantes de dominio

1. Nenhuma combinacao `recurrence_rule_id + competence_month` pode gerar mais de
   uma ocorrencia.
2. Nao existe exclusao de recorrencia; historico deve ser preservado.
3. Alteracoes afetam apenas competencias ainda nao geradas.
4. `start_competence_month` nao pode mudar apos primeira geracao.
5. Geracao bloqueada por dados invalidos deve retornar motivo acionavel.
