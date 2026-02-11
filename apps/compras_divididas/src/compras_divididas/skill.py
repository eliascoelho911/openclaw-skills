"""OpenClaw skill bootstrap for compras-divididas."""

from __future__ import annotations

import json
from typing import Any

from compras_divididas.api.monthly_closures import create_monthly_closure


def _format_rejected_line(item: dict[str, object]) -> str:
    message_id = str(item.get("message_id", ""))
    reason_code = str(item.get("reason_code", ""))
    reason_message = str(item.get("reason_message", ""))
    return f"- {message_id}: {reason_code} ({reason_message})"


def _format_valid_line(item: dict[str, object]) -> str:
    author_external_id = str(item.get("author_external_id", ""))
    description = str(item.get("description", ""))
    amount_brl = str(item.get("amount_brl", ""))
    return f"- {author_external_id}: {description} -> {amount_brl}"


def _format_deduplicated_line(item: dict[str, object]) -> str:
    message_id = str(item.get("message_id", ""))
    duplicated_of_entry_id = str(item.get("duplicated_of_entry_id", ""))
    reason_message = str(item.get("reason_message", ""))
    return f"- {message_id}: duplicated of {duplicated_of_entry_id} ({reason_message})"


def _render_skill_response(payload: dict[str, Any]) -> str:
    transfer = payload["transfer_instruction"]
    counts = payload["counts"]
    valid_entries = payload.get("valid_entries", [])
    rejected_entries = payload.get("rejected_entries", [])
    deduplicated_entries = payload.get("deduplicated_entries", [])

    if not isinstance(transfer, dict) or not isinstance(counts, dict):
        return "Unable to render closure response."

    summary_lines = [
        "Resumo executivo",
        f"- Pagador: {transfer['payer_external_id'] or '-'}",
        f"- Recebedor: {transfer['receiver_external_id'] or '-'}",
        f"- Valor: {transfer['amount_brl']}",
        (
            "- Contagens: "
            f"validos={counts['valid']}, "
            f"invalidos={counts['invalid']}, "
            f"ignorados={counts['ignored']}, "
            f"deduplicados={counts['deduplicated']}"
        ),
    ]

    details_lines = ["Detalhamento"]
    if isinstance(valid_entries, list) and valid_entries:
        details_lines.append("- Lancamentos validos:")
        details_lines.extend(
            _format_valid_line(item) for item in valid_entries if isinstance(item, dict)
        )
    if isinstance(rejected_entries, list) and rejected_entries:
        details_lines.append("- Lancamentos rejeitados:")
        details_lines.extend(
            _format_rejected_line(item)
            for item in rejected_entries
            if isinstance(item, dict)
        )
    if isinstance(deduplicated_entries, list) and deduplicated_entries:
        details_lines.append("- Lancamentos deduplicados:")
        details_lines.extend(
            _format_deduplicated_line(item)
            for item in deduplicated_entries
            if isinstance(item, dict)
        )

    if len(details_lines) == 1:
        details_lines.append("- Nenhum detalhe adicional.")

    return "\n".join([*summary_lines, "", *details_lines])


def handle_command(command_text: str) -> str:
    """Handle skill commands and return summary followed by details."""
    normalized_command = command_text.strip()
    if not normalized_command:
        return "Provide a command to start a monthly closure."

    if not normalized_command.startswith("fechar "):
        return (
            "Unsupported command. Use: fechar <json_payload> to process "
            "a monthly closure."
        )

    raw_payload = normalized_command.removeprefix("fechar ").strip()
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return "Invalid JSON payload. Use: fechar <json_payload>."

    status_code, response = create_monthly_closure(payload)
    if status_code != 201:
        message = str(response.get("message", "Unable to process closure."))
        details = response.get("details")
        if isinstance(details, list) and details:
            return f"{message}\n- " + "\n- ".join(str(item) for item in details)
        return message

    return _render_skill_response(response)
