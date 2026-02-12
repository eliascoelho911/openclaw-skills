---
name: compras-divididas-mcp
description: Operate the compras_divididas MCP/API to register and manage recurrences, purchases and refunds, search movements and recurrences with monthly filters, and fetch monthly summary/report reconciliation between two participants. Use when the request involves the tools list_participants, create_recurrence, list_recurrences, edit_recurrence, end_recurrence, list_movements, create_movement, get_monthly_summary, or get_monthly_report, including WhatsApp ingestion, external_id deduplication, and API error diagnosis.
---

# Compras Divididas MCP

Use this skill to operate the monthly reconciliation flow via the compras_divididas MCP server, without manual HTTP calls.

## Operating flow

1. Validate connectivity by calling `list_participants` at the start of the session.
2. Map the returned `participant_id` values and reuse those exact IDs in all other tools.
3. Select the right tool for the user's intent:
    - Register a recurrence: `create_recurrence`
    - Installment shorthand (for example `500 12x` or `500x12`): `create_recurrence`
    - List recurrence lifecycle/status: `list_recurrences`
    - Edit recurrence settings: `edit_recurrence`
    - End a recurrence logically: `end_recurrence`
    - Register a purchase or refund: `create_movement`
    - Find a purchase for a refund: `list_movements`
    - Check the month partials: `get_monthly_summary` (always send `auto_generate=true`)
    - Get the on-demand consolidated report: `get_monthly_report` (always send `auto_generate=true`)
4. Validate the result using canonical fields (`id`, `competence_month`, `total_net`, `transfer`).
5. Handle failures using the playbook in `references/api_reference.md`.
6. After each tool call, always answer with the PT-BR template from `references/response_templates.md`, with no extra text outside the selected template.

## Critical rules

- Send `amount` as a 2-decimal string (`"120.50"`), never as a float.
- For recurrence operations, always use a 50/50 split with `split_config={"mode":"equal"}`.
- Send `external_id` for WhatsApp/integration events to enable safe deduplication.
- Do not guess `participant_id`; discover it with `list_participants` before creating movements.
- Send `occurred_at` when backfilling history; if omitted, the API uses the current timestamp in `America/Sao_Paulo`.
- Create refunds only with an original purchase reference (`original_purchase_id` or `original_purchase_external_id`).
- Keep post-tool messages direct, in Portuguese, and with emoji.
- Template compliance is mandatory: select exactly one template variant for the executed tool (`success`, `error`, or `empty`) and only replace placeholders.
- Do not add headings, explanations, JSON dumps, tool traces, or any extra lines before/after the template output.

## Intent mapping for installment shorthand

- Treat installment expressions as recurrence creation (`create_recurrence`), not as one-off purchases (`create_movement`).
- Supported shorthand patterns:
  - `<description> <amount> <installments>x` (example: `Smartphone 500 12x`)
  - `<description> <amount>x<installments>` (example: `Smartphone 500x12`)
- Parsing rules:
  - `description`: text before the amount token.
  - `amount`: installment amount, normalized to a 2-decimal string (`"500.00"`).
  - `installments`: integer after `x`; when `installments >= 2`, create a fixed-duration recurrence.
- Recurrence payload construction for shorthand:
  - `start_competence_month`: month provided by user; otherwise current competence month.
  - `end_competence_month`: `start_competence_month + installments - 1` months (inclusive).
  - `reference_day`: explicit day from user; otherwise current day in `America/Sao_Paulo`.
  - `split_config`: always `{"mode":"equal"}`.
- Only use `create_movement` for these patterns when the user explicitly asks to register a single purchase.

## Recommended sequences

### Register a purchase

1. Call `list_participants` and map the sender to `requested_by_participant_id`.
2. Call `create_movement` with `type="purchase"`, `amount`, `description`, and `external_id` (when available).
3. Persist the returned `id` to make future refunds easier.

### Register a recurrence

1. Call `list_participants` and map valid participant IDs.
2. Call `create_recurrence` with `description`, `amount`, `payer_participant_id`, `requested_by_participant_id`, `split_config={"mode":"equal"}`, `reference_day`, and `start_competence_month`.
3. Optionally include `end_competence_month` for fixed-duration recurrences.
4. Confirm `status=active` and keep the returned recurrence `id` for future lifecycle operations.

### Manage recurrence lifecycle

1. Call `list_recurrences` with optional filters (`status`, `year`, `month`, `limit`, `offset`) to locate target rules.
2. Call `edit_recurrence` to update fields (for example `amount`, `description`, `reference_day`) while keeping `split_config={"mode":"equal"}`.
3. Use `clear_end_competence_month=true` in `edit_recurrence` when you need to remove an existing end month.
4. Call `end_recurrence` to end a recurrence logically (status transition to `ended`), optionally passing `end_competence_month`.

### Register a refund without a `purchase_id`

1. Call `list_movements` with `year`, `month`, and filters (`type="purchase"`, `amount`, `description`, `participant_id`, `external_id`) to locate the purchase.
2. Prefer `original_purchase_id` when it is available.
3. Use `original_purchase_external_id` when the `purchase_id` is not available and the external identifier is trustworthy.

### Close the monthly reconciliation

1. Call `get_monthly_summary` with `auto_generate=true` to validate the partials.
2. Call `get_monthly_report` with `auto_generate=true` for the on-demand consolidated view (same response schema).
3. Communicate `transfer.amount`, `transfer.debtor_participant_id`, and `transfer.creditor_participant_id`.

### Auto-generate recurrent entries before consultation

1. Always call `get_monthly_summary` and `get_monthly_report` with `auto_generate=true`.
2. Do not use `auto_generate=false` in this skill.

## Detailed reference

Read `references/api_reference.md` for the full contract for each tool:

- required and optional parameters
- validations and limits
- response format
- common errors and corrective action

Read `references/response_templates.md` to format every post-tool answer:

- one success template and one failure template per tool
- direct PT-BR text with emojis
- placeholders with deterministic filling rules
- mandatory output contract for every tool response

## Response formatting policy

- Never answer raw JSON after using a tool.
- Always convert the result to the corresponding PT-BR template.
- Keep at most 3-6 lines when possible.
- Include only actionable fields (IDs, values, competence month, transfer).
- Respect the template line order and labels exactly as documented.
- If a placeholder value is missing, apply the fallback rules in `references/response_templates.md` instead of inventing new wording.
