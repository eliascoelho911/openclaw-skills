---
name: compras-divididas-mcp
description: Operate the compras_divididas MCP/API to register recurring transactions, purchases and refunds, search movements with monthly filters, and fetch monthly summary/report reconciliation between two participants. Use when the request involves the tools list_participants, create_recurrence, list_movements, create_movement, get_monthly_summary, or get_monthly_report, including WhatsApp ingestion, external_id deduplication, and API error diagnosis.
---

# Compras Divididas MCP

Use this skill to operate the monthly reconciliation flow via the compras_divididas MCP server, without manual HTTP calls.

## Operating flow

1. Validate connectivity by calling `list_participants` at the start of the session.
2. Map the returned `participant_id` values and reuse those exact IDs in all other tools.
3. Select the right tool for the user's intent:
   - Register a recurrence: `create_recurrence`
   - Register a purchase or refund: `create_movement`
   - Find a purchase for a refund: `list_movements`
   - Check the month partials: `get_monthly_summary` (`auto_generate` optional)
   - Get the on-demand consolidated report: `get_monthly_report` (`auto_generate` optional)
4. Validate the result using canonical fields (`id`, `competence_month`, `total_net`, `transfer`).
5. Handle failures using the playbook in `references/api_reference.md`.
6. After each tool call, always answer with the PT-BR template from `references/response_templates.md`.

## Critical rules

- Send `amount` as a 2-decimal string (`"120.50"`), never as a float.
- Send `external_id` for WhatsApp/integration events to enable safe deduplication.
- Do not guess `participant_id`; discover it with `list_participants` before creating movements.
- Send `occurred_at` when backfilling history; if omitted, the API uses the current timestamp in `America/Sao_Paulo`.
- Create refunds only with an original purchase reference (`original_purchase_id` or `original_purchase_external_id`).
- Keep post-tool messages direct, in Portuguese, and with emoji.

## Recommended sequences

### Register a purchase

1. Call `list_participants` and map the sender to `requested_by_participant_id`.
2. Call `create_movement` with `type="purchase"`, `amount`, `description`, and `external_id` (when available).
3. Persist the returned `id` to make future refunds easier.

### Register a recurrence

1. Call `list_participants` and map valid participant IDs.
2. Call `create_recurrence` with `description`, `amount`, `payer_participant_id`, `requested_by_participant_id`, `split_config`, `reference_day`, and `start_competence_month`.
3. Optionally include `end_competence_month` for fixed-duration recurrences.
4. Confirm `status=active` and keep the returned recurrence `id` for future lifecycle operations.

### Register a refund without a `purchase_id`

1. Call `list_movements` with `year`, `month`, and filters (`type="purchase"`, `amount`, `description`, `participant_id`, `external_id`) to locate the purchase.
2. Prefer `original_purchase_id` when it is available.
3. Use `original_purchase_external_id` when the `purchase_id` is not available and the external identifier is trustworthy.

### Close the monthly reconciliation

1. Call `get_monthly_summary` to validate the partials.
2. Call `get_monthly_report` for the on-demand consolidated view (same response schema).
3. Communicate `transfer.amount`, `transfer.debtor_participant_id`, and `transfer.creditor_participant_id`.

### Auto-generate recurrent entries before consultation

1. When the user asks to include recurring entries automatically, call `get_monthly_summary` or `get_monthly_report` with `auto_generate=true`.
2. Use `auto_generate=false` (default) when the user wants to inspect only existing posted movements.

## Detailed reference

Read `references/api_reference.md` for the full contract for each tool:

- required and optional parameters
- validations and limits
- response format
- common errors and corrective action

Read `references/response_templates.md` to format every post-tool answer:

- one success template and one failure template per tool
- direct PT-BR text with emojis
- placeholders ready for script-based filling
- optional renderer: `scripts/render_tool_response.py`

## Response formatting policy

- Never answer raw JSON after using a tool.
- Always convert the result to the corresponding PT-BR template.
- Keep at most 3-6 lines when possible.
- Include only actionable fields (IDs, values, competence month, transfer).
