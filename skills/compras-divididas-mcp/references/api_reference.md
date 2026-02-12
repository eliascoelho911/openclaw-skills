# API/MCP Reference - compras_divididas

## Table of contents

1. Global conventions
2. Tool `list_participants`
3. Tool `list_movements`
4. Tool `create_recurrence`
5. Tool `list_recurrences`
6. Tool `edit_recurrence`
7. Tool `end_recurrence`
8. Tool `create_movement`
9. Tool `get_monthly_summary`
10. Tool `get_monthly_report`
11. Response templates (PT-BR)
12. MCP error handling and recovery

## Global conventions

- Assume the MCP server is already installed and connected.
- Each MCP tool proxies to an internal REST endpoint:
  - `list_participants` -> `GET /v1/participants`
  - `list_movements` -> `GET /v1/movements`
  - `create_recurrence` -> `POST /v1/recurrences`
  - `list_recurrences` -> `GET /v1/recurrences`
  - `edit_recurrence` -> `PATCH /v1/recurrences/{recurrence_id}`
  - `end_recurrence` -> `POST /v1/recurrences/{recurrence_id}/end`
  - `create_movement` -> `POST /v1/movements`
  - `get_monthly_summary` -> `GET /v1/months/{year}/{month}/summary`
  - `get_monthly_report` -> `GET /v1/months/{year}/{month}/report`
- Treat money values as 2-decimal strings (`"10.00"`).
- Use the competence timezone `America/Sao_Paulo` when interpreting monthly consolidation.
- Call `list_participants` at the start of the session and reuse the returned IDs.
- After every tool execution, format the user-facing answer using `references/response_templates.md`.

### Intent mapping for installment shorthand

- Interpret messages like `Smartphone 500 12x` or `Smartphone 500x12` as recurrence intent.
- Parse the value before `x` as installment amount and normalize to 2 decimals.
- Parse the value after `x` as installment count.
- When installment count is `>= 2`, call `create_recurrence` (not `create_movement`).
- Build fixed-duration recurrence by deriving `end_competence_month` as `start + installments - 1` months (inclusive).
- Use user-provided `start_competence_month`/`reference_day` when available; otherwise default to current competence month and current day in `America/Sao_Paulo`.

## Tool `list_participants`

### Purpose

List the two active participants used by reconciliation.

### Input contract

- Accept no parameters.
- Send an empty payload `{}` when calling the tool.

### Output contract

- Return an object:
  - `participants`: list of participants
    - `id` (string)
    - `display_name` (string)
    - `is_active` (boolean)

### Usage pattern

1. Call this tool first.
2. Capture the `id` for each participant.
3. Reuse those IDs in `create_movement` and `list_movements` filters.

### Example tool call

```json
{
  "tool": "list_participants",
  "arguments": {}
}
```

## Tool `list_movements`

### Purpose

Search movements for a month with optional filters and pagination.

### Input contract

- Required:
  - `year` (int, 2000..2100)
  - `month` (int, 1..12)
- Optional:
  - `type` (`"purchase"` or `"refund"`)
  - `description` (string, 1..280)
  - `amount` (string decimal, regex `^[0-9]+\.[0-9]{2}$`)
  - `participant_id` (string)
  - `external_id` (string, max 120)
  - `limit` (int, 1..200, default `50`)
  - `offset` (int, >= 0, default `0`)

### Filtering behavior

- Apply `description` as a case-insensitive partial match (`contains`).
- Apply `amount` as exact equality after money normalization to 2 decimals.
- Apply `participant_id` against the effective payer (`payer_participant_id`).
- Apply `external_id` as exact equality.
- Sort by `occurred_at desc`, then `created_at desc`.

### Output contract

- Return an object:
  - `items`: lista de `MovementResponse`
    - `id`, `type`, `amount`, `description`, `occurred_at`, `competence_month`
    - `payer_participant_id`, `requested_by_participant_id`
    - `external_id`, `original_purchase_id`, `created_at`
  - `total`: total records before pagination
  - `limit`: applied page size
  - `offset`: applied offset

### Example tool call

```json
{
  "tool": "list_movements",
  "arguments": {
    "year": 2026,
    "month": 2,
    "type": "purchase",
    "description": "mercado",
    "amount": "120.00",
    "participant_id": "elias",
    "external_id": "wpp-101",
    "limit": 20,
    "offset": 0
  }
}
```

### Common mistakes

- Sending `amount` as a number (`120`) instead of a string (`"120.00"`).
- Omitting `year` or `month`.
- Using `limit` greater than `200`.

## Tool `create_recurrence`

### Purpose

Create one monthly recurrence in active status.

### Input contract

- Required:
  - `description` (string, 1..280)
  - `amount` (string decimal, regex `^[0-9]+\.[0-9]{2}$`)
  - `payer_participant_id` (string)
  - `requested_by_participant_id` (string)
  - `split_config` (object)
  - `reference_day` (int, 1..31)
  - `start_competence_month` (string `YYYY-MM`)
- Optional:
  - `end_competence_month` (string `YYYY-MM`)

### Domain rules

- Validate positive amount and non-empty description.
- Validate month range when `end_competence_month` is provided (`end >= start`).
- Recurrence is created with `status=active`.
- `next_competence_month` is calculated by API based on schedule rules.
- Skill policy: always send `split_config={"type":"equal"}` (50/50).

### Output contract (`RecurrenceResponse`)

- `id` (UUID)
- `description` (string)
- `amount` (money string)
- `payer_participant_id` (string)
- `requested_by_participant_id` (string)
- `split_config` (object)
- `periodicity` (`monthly`)
- `reference_day` (int)
- `start_competence_month` (`YYYY-MM`)
- `end_competence_month` (`YYYY-MM` or null)
- `status` (`active`, `paused`, `ended`)
- `first_generated_competence_month` (`YYYY-MM` or null)
- `last_processed_competence_month` (`YYYY-MM` or null)
- `next_competence_month` (`YYYY-MM`)
- `created_at` (datetime)
- `updated_at` (datetime)

### Example tool call

```json
{
  "tool": "create_recurrence",
  "arguments": {
    "description": "Aluguel",
    "amount": "1500.00",
    "payer_participant_id": "elias",
    "requested_by_participant_id": "elias",
    "split_config": {"type": "equal"},
    "reference_day": 5,
    "start_competence_month": "2026-03",
    "end_competence_month": "2026-12"
  }
}
```

### Error matrix

- `400 INVALID_REQUEST`
  - invalid payload fields
  - month filters inconsistent
- `422 DOMAIN_INVARIANT_VIOLATION`
  - recurrence business rules violated

## Tool `list_recurrences`

### Purpose

List recurrence rules with optional lifecycle/month filters.

### Input contract

- Optional:
  - `status` (`"active"`, `"paused"`, `"ended"`)
  - `year` (int, 2000..2100)
  - `month` (int, 1..12)
  - `limit` (int, 1..200, default `50`)
  - `offset` (int, >= 0, default `0`)

### Domain rules

- `year` and `month` must be provided together.
- When `year/month` are sent, filtering uses the competence month (`YYYY-MM-01`).

### Output contract (`RecurrenceListResponse`)

- `items`: list of `RecurrenceResponse`
- `total`: total records before pagination
- `limit`: applied page size
- `offset`: applied offset

### Example tool call

```json
{
  "tool": "list_recurrences",
  "arguments": {
    "status": "active",
    "year": 2026,
    "month": 4,
    "limit": 20,
    "offset": 0
  }
}
```

### Common mistakes

- Sending only `year` or only `month`.
- Using `limit` above `200`.

## Tool `edit_recurrence`

### Purpose

Partially update an existing recurrence rule.

### Input contract

- Required:
  - `recurrence_id` (UUID string)
  - `requested_by_participant_id` (string)
- Optional (at least one):
  - `description` (string, 1..280)
  - `amount` (string decimal, regex `^[0-9]+\.[0-9]{2}$`)
  - `payer_participant_id` (string)
  - `split_config` (object)
  - `reference_day` (int, 1..31)
  - `start_competence_month` (string `YYYY-MM`)
  - `end_competence_month` (string `YYYY-MM`)
  - `clear_end_competence_month` (bool, optional) for explicitly clearing end month

### Domain rules

- Use `clear_end_competence_month=true` to send `end_competence_month=null`.
- Do not send `end_competence_month` together with `clear_end_competence_month=true`.
- API applies last-write-wins semantics.
- Skill policy: keep `split_config={"type":"equal"}` (50/50) whenever `split_config` is sent.

### Output contract

- Returns one updated `RecurrenceResponse`.

### Example tool call

```json
{
  "tool": "edit_recurrence",
  "arguments": {
    "recurrence_id": "fca2f2ee-2ca8-45f4-a5f4-4cf0082a4f91",
    "requested_by_participant_id": "elias",
    "amount": "1750.00",
    "reference_day": 8
  }
}
```

### Error matrix

- `400 INVALID_REQUEST`
  - invalid payload
  - no updatable field provided
- `404 RECURRENCE_NOT_FOUND`
  - recurrence does not exist
- `422 DOMAIN_INVARIANT_VIOLATION`
  - recurrence business rules violated

## Tool `end_recurrence`

### Purpose

Logically end a recurrence (status transition), without hard deletion.

### Input contract

- Required:
  - `recurrence_id` (UUID string)
  - `requested_by_participant_id` (string)
- Optional:
  - `end_competence_month` (string `YYYY-MM`)

### Domain rules

- This operation maps to `POST /v1/recurrences/{recurrence_id}/end`.
- It ends lifecycle generation for the rule instead of deleting history.

### Output contract

- Returns one updated `RecurrenceResponse` with `status="ended"`.

### Example tool call

```json
{
  "tool": "end_recurrence",
  "arguments": {
    "recurrence_id": "fca2f2ee-2ca8-45f4-a5f4-4cf0082a4f91",
    "requested_by_participant_id": "elias",
    "end_competence_month": "2026-09"
  }
}
```

### Error matrix

- `404 RECURRENCE_NOT_FOUND`
  - recurrence does not exist
- `422 DOMAIN_INVARIANT_VIOLATION`
  - invalid state transition

## Tool `create_movement`

### Purpose

Register a purchase (`purchase`) or refund (`refund`) using an append-only model.

### Input contract

- Required:
  - `type`: `"purchase"` or `"refund"`
  - `amount`: string decimal com 2 casas (`^[0-9]+\.[0-9]{2}$`)
  - `description`: non-empty string (1..280)
  - `requested_by_participant_id`: string
- Optional:
  - `occurred_at`: datetime ISO-8601
  - `payer_participant_id`: string (default = `requested_by_participant_id`)
  - `external_id`: string (max 120)
  - `original_purchase_id`: UUID (for refunds)
  - `original_purchase_external_id`: string (max 120, for refunds)

### Domain rules

- Validate `amount > 0` after money normalization (2 decimals, ROUND_HALF_UP).
- Trim whitespace from `description`, `external_id`, and `original_purchase_external_id`.
- Default `occurred_at` when absent, using `America/Sao_Paulo`.
- Interpret a timezone-less `occurred_at` as `America/Sao_Paulo` local time.
- Default `payer_participant_id` when absent.
- Require an original purchase reference for `refund`:
  - `original_purchase_id` or `original_purchase_external_id`
- Resolve `original_purchase_external_id` within the same competence month and same effective payer context.
- Reject original purchase references on `purchase`.
- Reject `external_id` duplicates within the scope:
  - `competence_month + payer_participant_id + external_id`
- Reject refunds when the cumulative refunded total exceeds the original purchase amount.

### Resolution order for refunds

- If both references are provided, resolve using `original_purchase_id` first.
- Use `original_purchase_external_id` only when `original_purchase_id` is not present.

### Output contract (`MovementResponse`)

- `id` (UUID)
- `type` (`purchase`/`refund`)
- `amount` (string com 2 casas)
- `description` (string)
- `occurred_at` (datetime)
- `competence_month` (`YYYY-MM`)
- `payer_participant_id` (string)
- `requested_by_participant_id` (string)
- `external_id` (string or null)
- `original_purchase_id` (UUID or null)
- `created_at` (datetime)

### Example tool call (purchase)

```json
{
  "tool": "create_movement",
  "arguments": {
    "type": "purchase",
    "amount": "89.90",
    "description": "Supermercado",
    "requested_by_participant_id": "elias",
    "external_id": "wpp-msg-2026-02-10-001"
  }
}
```

### Example tool call (refund by external id)

```json
{
  "tool": "create_movement",
  "arguments": {
    "type": "refund",
    "amount": "20.00",
    "description": "Returned item",
    "requested_by_participant_id": "elias",
    "original_purchase_external_id": "wpp-msg-2026-02-10-001"
  }
}
```

### Error matrix

- `400 INVALID_REQUEST`
  - invalid payload
  - `amount <= 0`
  - refund missing original reference
  - participants not active
  - purchase includes an original purchase reference
- `404 PURCHASE_NOT_FOUND`
  - original purchase not found for refund
- `409 DUPLICATE_EXTERNAL_ID`
  - `external_id` already used in the same month for the same payer
- `422 REFUND_LIMIT_EXCEEDED`
  - cumulative refunds exceed purchase amount
- `422 DOMAIN_INVARIANT_VIOLATION` or `422 PERSISTENCE_ERROR`
  - domain/persistence inconsistency

## Tool `get_monthly_summary`

### Purpose

Return the partial consolidation for the competence month.

### Input contract

- `year` (int, 2000..2100)
- `month` (int, 1..12)
- `auto_generate` (bool, optional, default `false`)
  - when `true`, API runs idempotent recurrence generation before computing the summary

### Output contract (`MonthlySummaryResponse`)

- `competence_month` (`YYYY-MM`)
- `total_gross` (money string)
- `total_refunds` (money string)
- `total_net` (money string)
- `participants` (list with exactly 2 items)
  - `participant_id`
  - `paid_total`
  - `share_due`
  - `net_balance`
- `transfer`
  - `amount`
  - `debtor_participant_id` (string or null)
  - `creditor_participant_id` (string or null)

### Example tool call

```json
{
  "tool": "get_monthly_summary",
  "arguments": {
    "year": 2026,
    "month": 2,
    "auto_generate": true
  }
}
```

### Common mistakes

- Using `month=13` (validation error).
- Interpreting `participants[].net_balance` without checking `transfer`.

## Tool `get_monthly_report`

### Purpose

Return the on-demand consolidated monthly report, with the same schema as `get_monthly_summary`.

### Input contract

- `year` (int, 2000..2100)
- `month` (int, 1..12)
- `auto_generate` (bool, optional, default `false`)
  - when `true`, API runs idempotent recurrence generation before computing the report

### Output contract

- Same `MonthlySummaryResponse` contract as `get_monthly_summary`.

### Example tool call

```json
{
  "tool": "get_monthly_report",
  "arguments": {
    "year": 2026,
    "month": 2,
    "auto_generate": true
  }
}
```

### Usage guidance

- Use `get_monthly_summary` for in-month tracking.
- Use `get_monthly_report` for the consolidated view you share at month close.
- Skill policy: always call both tools with `auto_generate=true`.

## Response templates (PT-BR)

- Use `references/response_templates.md` after each tool call.
- Keep template outputs short, direct, and emoji-based.
- Treat template usage as a hard contract: choose the matching variant (`success`, `error`, or `empty`) and do not add text outside the template.

## MCP error handling and recovery

### MCP error format

- The MCP proxy turns API failures into a text error, typically:
  - `API error <CODE>: <message> | details=<details>`
  - or `API request failed with status <status>: <payload>`

### Recovery playbook

1. Read the `CODE` and `message`.
2. Fix the payload based on the error matrix for the tool you used.
3. Re-run the same tool.
4. For deduplication (`DUPLICATE_EXTERNAL_ID`), treat it as a possible legitimate retry:
   - query `list_movements` using `year`, `month`, `participant_id`, `external_id`
   - verify the equivalent movement already exists before trying to create again
5. For `PURCHASE_NOT_FOUND` on refunds:
   - locate the purchase with `list_movements`
   - re-send the refund with the correct `original_purchase_id`

### Infra troubleshooting

- If all tools fail due to connectivity, verify the target API is online at `MCP_API_BASE_URL`.
- If timeouts are frequent, increase `MCP_API_TIMEOUT_SECONDS` on the MCP server.
