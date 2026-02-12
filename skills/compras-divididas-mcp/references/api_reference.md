# API/MCP Reference - compras_divididas

## Table of contents

1. Global conventions
2. Tool `list_participants`
3. Tool `list_movements`
4. Tool `create_movement`
5. Tool `get_monthly_summary`
6. Tool `get_monthly_report`
7. Response templates (PT-BR)
8. MCP error handling and recovery

## Global conventions

- Assume the MCP server is already installed and connected.
- Each MCP tool proxies to an internal REST endpoint:
  - `list_participants` -> `GET /v1/participants`
  - `list_movements` -> `GET /v1/movements`
  - `create_movement` -> `POST /v1/movements`
  - `get_monthly_summary` -> `GET /v1/months/{year}/{month}/summary`
  - `get_monthly_report` -> `GET /v1/months/{year}/{month}/report`
- Treat money values as 2-decimal strings (`"10.00"`).
- Use the competence timezone `America/Sao_Paulo` when interpreting monthly consolidation.
- Call `list_participants` at the start of the session and reuse the returned IDs.
- After every tool execution, format the user-facing answer using `references/response_templates.md`.

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

## Response templates (PT-BR)

- Use `references/response_templates.md` after each tool call.
- Prefer the script `scripts/render_tool_response.py` when you have JSON output and need consistent formatting.
- Keep template outputs short, direct, and emoji-based.

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
