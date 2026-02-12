#!/usr/bin/env python3
"""Render PT-BR emoji response templates for compras_divididas MCP tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _get(data: dict[str, Any], key: str, default: str = "-") -> str:
    value = data.get(key)
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _type_label(value: str) -> str:
    if value == "purchase":
        return "Compra"
    if value == "refund":
        return "Estorno"
    return value


def _recurrence_status_label(value: str) -> str:
    if value == "active":
        return "Ativa"
    if value == "paused":
        return "Pausada"
    if value == "ended":
        return "Encerrada"
    return value


def _compute_installments(
    start_competence_month: str,
    end_competence_month: str,
) -> int | None:
    try:
        start_year_text, start_month_text = start_competence_month.split(
            "-", maxsplit=1
        )
        end_year_text, end_month_text = end_competence_month.split("-", maxsplit=1)
        start_year = int(start_year_text)
        start_month = int(start_month_text)
        end_year = int(end_year_text)
        end_month = int(end_month_text)
    except (ValueError, TypeError):
        return None

    if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
        return None

    diff = (end_year - start_year) * 12 + (end_month - start_month)
    if diff < 0:
        return None
    return diff + 1


def _transfer_sentence(data: dict[str, Any]) -> str:
    transfer = data.get("transfer")
    if not isinstance(transfer, dict):
        return "Sem transferencia no mes."

    amount = _get(transfer, "amount")
    debtor = _get(transfer, "debtor_participant_id")
    creditor = _get(transfer, "creditor_participant_id")

    if amount == "0.00" or debtor == "-" or creditor == "-":
        return "Sem transferencia no mes."
    return f"R$ {amount} de {debtor} para {creditor}."


def _generation_note(data: dict[str, Any]) -> str:
    auto_generate = data.get("auto_generate")
    if auto_generate is True:
        return "Inclui geracao automatica de recorrencias desta competencia."
    return "Considera somente movimentacoes ja registradas."


def _extract_error(data: dict[str, Any]) -> tuple[str, str]:
    code = _get(data, "code", "UNKNOWN_ERROR")
    message = _get(data, "message", "Unknown error")

    error = data.get("error")
    if isinstance(error, dict):
        code = _get(error, "code", code)
        message = _get(error, "message", message)

    return code, message


def _suggested_action(code: str) -> str:
    mapping = {
        "DUPLICATE_EXTERNAL_ID": (
            "Use list_movements para confirmar duplicidade antes de reenviar."
        ),
        "PURCHASE_NOT_FOUND": (
            "Localize a compra com list_movements e envie original_purchase_id correto."
        ),
        "REFUND_LIMIT_EXCEEDED": (
            "Ajuste o valor do estorno para nao exceder o total da compra."
        ),
        "INVALID_REQUEST": "Revise campos obrigatorios e formato dos valores.",
        "RECURRENCE_NOT_FOUND": "Confirme o recurrence_id e tente novamente.",
    }
    return mapping.get(code, "Revise os parametros e tente novamente.")


def render_list_participants(status: str, data: dict[str, Any]) -> str:
    if status == "error":
        code, message = _extract_error(data)
        return (
            "❌ Nao consegui listar os participantes.\n"
            f"- Codigo: {code}\n"
            f"- Mensagem: {message}\n"
            "➡️ Verifique conexao MCP/API e tente novamente."
        )

    participants = data.get("participants")
    if not isinstance(participants, list) or len(participants) < 1:
        return "🔎 Nenhum participante retornado."

    lines = ["👥 Participantes ativos:"]
    for participant in participants[:2]:
        if isinstance(participant, dict):
            pid = _get(participant, "id")
            name = _get(participant, "display_name")
            lines.append(f"- {pid} - {name}")
    lines.append("✅ IDs mapeados para as proximas operacoes.")
    return "\n".join(lines)


def render_list_movements(status: str, data: dict[str, Any]) -> str:
    if status == "error":
        code, message = _extract_error(data)
        return (
            "❌ Falha ao listar movimentacoes.\n"
            f"- Codigo: {code}\n"
            f"- Mensagem: {message}\n"
            '➡️ Revise year/month e filtros (amount no formato "0.00").'
        )

    items = data.get("items")
    if not isinstance(items, list) or len(items) == 0 or status == "empty":
        return "🔎 Nenhuma movimentacao encontrada com os filtros informados."

    total = _get(data, "total", str(len(items)))
    shown = str(min(len(items), 5))
    competence_month = "-"
    first = items[0]
    if isinstance(first, dict):
        competence_month = _get(first, "competence_month")

    bullet_lines: list[str] = []
    for item in items[:5]:
        if isinstance(item, dict):
            movement_id = _get(item, "id")
            movement_type = _type_label(_get(item, "type"))
            amount = _get(item, "amount")
            description = _get(item, "description")
            bullet_lines.append(
                f"- {movement_id} | {movement_type} | R$ {amount} | {description}"
            )
    if len(items) > 5:
        bullet_lines.append("...")

    header = (
        f"📚 Movimentacoes de {competence_month} (total: {total}, exibindo: {shown}):"
    )
    return f"{header}\n" + "\n".join(bullet_lines) + "\n✅ Consulta concluida."


def render_create_movement(status: str, data: dict[str, Any]) -> str:
    if status == "error":
        code, message = _extract_error(data)
        action = _suggested_action(code)
        return (
            "❌ Nao foi possivel registrar a movimentacao.\n"
            f"- Codigo: {code}\n"
            f"- Mensagem: {message}\n"
            f"➡️ Acao recomendada: {action}"
        )

    movement_type = _type_label(_get(data, "type"))
    movement_id = _get(data, "id")
    amount = _get(data, "amount")
    competence_month = _get(data, "competence_month")
    payer = _get(data, "payer_participant_id")
    external_id = _get(data, "external_id")

    return (
        "🧾 Movimentacao registrada com sucesso!\n"
        f"- Tipo: {movement_type}\n"
        f"- ID: {movement_id}\n"
        f"- Valor: R$ {amount}\n"
        f"- Competencia: {competence_month}\n"
        f"- Pagador: {payer}\n"
        f"🔁 external_id: {external_id}"
    )


def render_create_recurrence(status: str, data: dict[str, Any]) -> str:
    if status == "error":
        code, message = _extract_error(data)
        action = _suggested_action(code)
        return (
            "❌ Nao foi possivel criar a recorrencia.\n"
            f"- Codigo: {code}\n"
            f"- Mensagem: {message}\n"
            f"➡️ Acao recomendada: {action}"
        )

    recurrence_id = _get(data, "id")
    description = _get(data, "description")
    amount = _get(data, "amount")
    start_competence_month = _get(data, "start_competence_month")
    end_competence_month = _get(data, "end_competence_month", "-")

    recurrence_kind = "Fixa"
    installments = "Ilimitada"
    if end_competence_month != "-":
        recurrence_kind = "Parcelada"
        installments_count = _compute_installments(
            start_competence_month,
            end_competence_month,
        )
        installments = (
            str(installments_count) if installments_count is not None else "Indefinida"
        )

    return (
        "🔁 Recorrencia criada com sucesso!\n"
        f"- ID: {recurrence_id}\n"
        f"- Descricao: {description}\n"
        f"- Valor: R$ {amount}\n"
        f"- Tipo: {recurrence_kind}\n"
        f"- Parcelas: {installments}\n"
        f"- Inicio: {start_competence_month}\n"
        f"- Fim: {end_competence_month}"
    )


def render_list_recurrences(status: str, data: dict[str, Any]) -> str:
    if status == "error":
        code, message = _extract_error(data)
        return (
            "❌ Falha ao listar recorrencias.\n"
            f"- Codigo: {code}\n"
            f"- Mensagem: {message}\n"
            "➡️ Revise filtros de status/year/month e tente novamente."
        )

    items = data.get("items")
    if not isinstance(items, list) or len(items) == 0 or status == "empty":
        return "🔎 Nenhuma recorrencia encontrada com os filtros informados."

    total = _get(data, "total", str(len(items)))
    shown = str(min(len(items), 5))

    bullet_lines: list[str] = []
    for item in items[:5]:
        if isinstance(item, dict):
            recurrence_id = _get(item, "id")
            recurrence_status = _recurrence_status_label(_get(item, "status"))
            amount = _get(item, "amount")
            reference_day = _get(item, "reference_day")
            description = _get(item, "description")
            bullet_lines.append(
                f"- {recurrence_id} | {recurrence_status}"
                f" | R$ {amount} | dia {reference_day} | {description}"
            )
    if len(items) > 5:
        bullet_lines.append("...")

    header = f"🗂️ Recorrencias encontradas (total: {total}, exibindo: {shown}):"
    return f"{header}\n" + "\n".join(bullet_lines) + "\n✅ Consulta concluida."


def render_edit_recurrence(status: str, data: dict[str, Any]) -> str:
    if status == "error":
        code, message = _extract_error(data)
        action = _suggested_action(code)
        return (
            "❌ Nao foi possivel atualizar a recorrencia.\n"
            f"- Codigo: {code}\n"
            f"- Mensagem: {message}\n"
            f"➡️ Acao recomendada: {action}"
        )

    recurrence_id = _get(data, "id")
    description = _get(data, "description")
    amount = _get(data, "amount")
    reference_day = _get(data, "reference_day")
    recurrence_status = _recurrence_status_label(_get(data, "status"))
    start_competence_month = _get(data, "start_competence_month")
    end_competence_month = _get(data, "end_competence_month", "-")

    return (
        "✏️ Recorrencia atualizada com sucesso!\n"
        f"- ID: {recurrence_id}\n"
        f"- Descricao: {description}\n"
        f"- Valor: R$ {amount}\n"
        f"- Dia de referencia: {reference_day}\n"
        f"- Status: {recurrence_status}\n"
        f"📆 Vigencia: {start_competence_month} ate {end_competence_month}"
    )


def render_end_recurrence(status: str, data: dict[str, Any]) -> str:
    if status == "error":
        code, message = _extract_error(data)
        action = _suggested_action(code)
        return (
            "❌ Nao foi possivel encerrar a recorrencia.\n"
            f"- Codigo: {code}\n"
            f"- Mensagem: {message}\n"
            f"➡️ Acao recomendada: {action}"
        )

    recurrence_id = _get(data, "id")
    recurrence_status = _recurrence_status_label(_get(data, "status"))
    end_competence_month = _get(data, "end_competence_month", "-")

    return (
        "🛑 Recorrencia encerrada com sucesso.\n"
        f"- ID: {recurrence_id}\n"
        f"- Status: {recurrence_status}\n"
        f"- Fim efetivo: {end_competence_month}\n"
        "✅ Nenhum novo lancamento sera gerado para esta regra apos o encerramento."
    )


def _monthly_common(emoji: str, title: str, data: dict[str, Any], footer: str) -> str:
    competence_month = _get(data, "competence_month")
    total_gross = _get(data, "total_gross")
    total_refunds = _get(data, "total_refunds")
    total_net = _get(data, "total_net")

    participants = data.get("participants")
    p1 = {"participant_id": "-", "paid_total": "-", "net_balance": "-"}
    p2 = {"participant_id": "-", "paid_total": "-", "net_balance": "-"}
    if isinstance(participants, list):
        if len(participants) > 0 and isinstance(participants[0], dict):
            p1 = participants[0]
        if len(participants) > 1 and isinstance(participants[1], dict):
            p2 = participants[1]

    transfer_sentence = _transfer_sentence(data)
    generation_note = _generation_note(data)

    lines = [
        f"{emoji} {title} {competence_month}",
        f"- {generation_note}",
        f"- Bruto: R$ {total_gross}",
        f"- Estornos: R$ {total_refunds}",
        f"- Liquido: R$ {total_net}",
        (
            f"- {_get(p1, 'participant_id')}: pagou R$ {_get(p1, 'paid_total')}"
            f" | saldo {_get(p1, 'net_balance')}"
        ),
        (
            f"- {_get(p2, 'participant_id')}: pagou R$ {_get(p2, 'paid_total')}"
            f" | saldo {_get(p2, 'net_balance')}"
        ),
        f"💸 Transferencia: {transfer_sentence}",
    ]
    if footer:
        lines.append(footer)
    return "\n".join(lines)


def render_get_monthly_summary(status: str, data: dict[str, Any]) -> str:
    if status == "error":
        code, message = _extract_error(data)
        return (
            "❌ Nao consegui gerar o resumo mensal.\n"
            f"- Codigo: {code}\n"
            f"- Mensagem: {message}\n"
            "➡️ Revise year/month e tente novamente."
        )
    return _monthly_common("📊", "Resumo mensal", data, "")


def render_get_monthly_report(status: str, data: dict[str, Any]) -> str:
    if status == "error":
        code, message = _extract_error(data)
        return (
            "❌ Nao consegui gerar o relatorio mensal.\n"
            f"- Codigo: {code}\n"
            f"- Mensagem: {message}\n"
            "➡️ Revise year/month e tente novamente."
        )
    return _monthly_common(
        "📄",
        "Relatorio consolidado",
        data,
        "✅ Fechamento pronto para compartilhar.",
    )


def render(tool: str, status: str, data: dict[str, Any]) -> str:
    if tool == "list_participants":
        return render_list_participants(status, data)
    if tool == "list_movements":
        return render_list_movements(status, data)
    if tool == "create_movement":
        return render_create_movement(status, data)
    if tool == "create_recurrence":
        return render_create_recurrence(status, data)
    if tool == "list_recurrences":
        return render_list_recurrences(status, data)
    if tool == "edit_recurrence":
        return render_edit_recurrence(status, data)
    if tool == "end_recurrence":
        return render_end_recurrence(status, data)
    if tool == "get_monthly_summary":
        return render_get_monthly_summary(status, data)
    if tool == "get_monthly_report":
        return render_get_monthly_report(status, data)
    raise ValueError(f"Unsupported tool: {tool}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True)
    parser.add_argument(
        "--status", default="success", choices=["success", "error", "empty"]
    )
    parser.add_argument("--json", required=True, dest="json_path")
    args = parser.parse_args()

    payload = json.loads(Path(args.json_path).read_text(encoding="utf-8"))
    output = render(args.tool, args.status, payload)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
