# Data Model - Reconciliacao Mensal de Compras Compartilhadas

## Visao geral

O modelo foi desenhado para:

1. Registrar compras e estornos em historico append-only.
2. Garantir consistencia monetaria (2 casas decimais) e deduplicacao por mes.
3. Congelar resultado do fechamento mensal para consulta idempotente.

## Entidades

### 1) Participant

Representa cada pessoa ativa no contexto de divisao.

| Campo | Tipo | Regra |
|-------|------|-------|
| id | UUID | PK |
| code | VARCHAR(32) | NOT NULL, UNIQUE |
| display_name | VARCHAR(120) | NOT NULL |
| is_active | BOOLEAN | NOT NULL, default `true` |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Regras de validacao**

- Deve haver exatamente dois participantes ativos para operacoes da v1.
- `code` e usado como identificador estavel para API e auditoria.

### 2) FinancialMovement

Registro append-only de compra ou estorno.

| Campo | Tipo | Regra |
|-------|------|-------|
| id | UUID | PK |
| movement_type | ENUM(`purchase`,`refund`) | NOT NULL |
| amount | NUMERIC(12,2) | NOT NULL, `> 0` |
| description | VARCHAR(280) | NOT NULL |
| occurred_at | TIMESTAMPTZ | NOT NULL (usa timestamp atual quando ausente no input) |
| competence_month | DATE | NOT NULL (primeiro dia do mes em America/Sao_Paulo) |
| payer_participant_id | UUID | FK -> `participants.id`, NOT NULL (default = `requested_by_participant_id` quando ausente no input) |
| requested_by_participant_id | UUID | FK -> `participants.id`, NOT NULL |
| external_id | VARCHAR(120) | NULL |
| original_purchase_id | UUID | FK -> `financial_movements.id`, NULL para compra, NOT NULL para estorno |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indices e constraints**

- PK em `id`.
- Indice parcial unico para deduplicacao:
  `(competence_month, payer_participant_id, external_id)` where
  `external_id IS NOT NULL`.
- Check de tipo:
  - `purchase` exige `original_purchase_id IS NULL`.
  - `refund` exige `original_purchase_id IS NOT NULL`.

**Regras de validacao**

- Arredondar `amount` para 2 casas no registro (ROUND_HALF_UP).
- Quando `occurred_at` nao for enviado, usar horario atual no timezone
  `America/Sao_Paulo` (persistido como `timestamptz`).
- Quando `payer_participant_id` nao for enviado, assumir
  `requested_by_participant_id`.
- Estorno deve referenciar compra existente por `original_purchase_id` ou por
  `original_purchase_external_id` (campo de input da API, nao persistido); antes
  de persistir, o sistema sempre resolve para `original_purchase_id`.
- Quando usar `original_purchase_external_id`, resolver compra do tipo
  `purchase` no mesmo `competence_month` do estorno e mesmo
  `payer_participant_id` efetivo.
- Soma de estornos vinculados nao pode ultrapassar o valor da compra original.
- Nao permitir escrita em mes ja fechado.

### 3) MonthlyClosure

Snapshot imutavel do fechamento de um mes.

| Campo | Tipo | Regra |
|-------|------|-------|
| id | UUID | PK |
| competence_month | DATE | NOT NULL, UNIQUE |
| total_gross | NUMERIC(12,2) | NOT NULL |
| total_refunds | NUMERIC(12,2) | NOT NULL |
| total_net | NUMERIC(12,2) | NOT NULL |
| transfer_amount | NUMERIC(12,2) | NOT NULL |
| debtor_participant_id | UUID | FK -> `participants.id`, NULL quando sem transferencia |
| creditor_participant_id | UUID | FK -> `participants.id`, NULL quando sem transferencia |
| closed_by_participant_id | UUID | FK -> `participants.id`, NOT NULL |
| closed_at | TIMESTAMPTZ | NOT NULL |
| movement_count | INTEGER | NOT NULL |

**Regras de validacao**

- Um unico fechamento por `competence_month`.
- Segunda chamada de fechamento do mesmo mes retorna o mesmo registro.
- A partir da existencia do fechamento, o mes torna-se imutavel para novas
  movimentacoes.

### 4) MonthlyClosureParticipant

Detalhamento do saldo individual no fechamento final.

| Campo | Tipo | Regra |
|-------|------|-------|
| closure_id | UUID | FK -> `monthly_closures.id`, PK composta |
| participant_id | UUID | FK -> `participants.id`, PK composta |
| paid_total | NUMERIC(12,2) | NOT NULL |
| share_due | NUMERIC(12,2) | NOT NULL |
| net_balance | NUMERIC(12,2) | NOT NULL |

**Regras de validacao**

- Exatamente duas linhas por fechamento (uma por participante ativo).
- `sum(net_balance)` deve ser `0.00`.

## Relacionamentos

- `participants (1) -> (N) financial_movements` por `payer_participant_id`.
- `participants (1) -> (N) financial_movements` por `requested_by_participant_id`.
- `financial_movements (purchase 1) -> (N refund)` por `original_purchase_id`.
- `monthly_closures (1) -> (2) monthly_closure_participants`.

## Estados e transicoes

### Ciclo do mes

`OPEN` -> `CLOSED`

- `OPEN`: aceita novas compras e estornos validos.
- `CLOSED`: rejeita qualquer nova movimentacao para aquela competencia.
- Reabertura nao faz parte da v1.

### Ciclo da movimentacao

`CREATED` (estado unico e imutavel)

- Nao existe update/delete.
- Correcao e feita por novo estorno + novo lancamento.

### Operacao de fechamento

`NOT_CLOSED` -> `CLOSED_SNAPSHOT`

- Primeiro fechamento persiste snapshot.
- Fechamentos subsequentes retornam o mesmo snapshot (idempotencia).

## Invariantes de dominio

1. Exatamente dois participantes ativos no contexto.
2. Todo valor monetario persistido tem duas casas decimais.
3. Nenhum estorno excede o valor da compra original.
4. Nenhuma movimentacao entra em mes fechado.
5. Duplicidade por external_id (mesmo participante + mesmo mes) e rejeitada.
6. Estorno por `original_purchase_external_id` deve resolver exatamente uma
   compra valida no contexto de mes + participante.
