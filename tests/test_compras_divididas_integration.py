from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from compras_divididas.application.use_cases.close_month import (
    CloseMonthRequest,
    CloseMonthUseCase,
)
from compras_divididas.cli import app
from compras_divididas.skill import handle_command


def _golden_dataset_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "apps"
        / "compras_divididas"
        / "tests"
        / "fixtures"
        / "golden"
        / "monthly_closure_dataset.json"
    )


def _parse_cli_summary(output: str) -> dict[str, object]:
    summary: dict[str, object] = {}
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("Pagador: "):
            summary["payer_external_id"] = line.removeprefix("Pagador: ")
        elif line.startswith("Recebedor: "):
            summary["receiver_external_id"] = line.removeprefix("Recebedor: ")
        elif line.startswith("Valor: "):
            summary["amount_brl"] = line.removeprefix("Valor: ")
        elif line.startswith("Validos: "):
            counts = line
            parts = [part.strip() for part in counts.split("|")]
            summary["counts"] = {
                "valid": int(parts[0].removeprefix("Validos: ").strip()),
                "invalid": int(parts[1].removeprefix("Invalidos: ").strip()),
                "ignored": int(parts[2].removeprefix("Ignorados: ").strip()),
                "deduplicated": int(parts[3].removeprefix("Deduplicados: ").strip()),
            }
    return summary


def _parse_skill_summary(output: str) -> dict[str, object]:
    summary: dict[str, object] = {}
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("- Pagador: "):
            summary["payer_external_id"] = line.removeprefix("- Pagador: ")
        elif line.startswith("- Recebedor: "):
            summary["receiver_external_id"] = line.removeprefix("- Recebedor: ")
        elif line.startswith("- Valor: "):
            summary["amount_brl"] = line.removeprefix("- Valor: ")
        elif line.startswith("- Contagens: "):
            pairs = line.removeprefix("- Contagens: ").split(",")
            parsed = {
                key.strip(): int(value.strip())
                for key, value in (pair.split("=", maxsplit=1) for pair in pairs)
            }
            summary["counts"] = {
                "valid": parsed["validos"],
                "invalid": parsed["invalidos"],
                "ignored": parsed["ignorados"],
                "deduplicated": parsed["deduplicados"],
            }
    return summary


def test_cli_and_skill_summary_are_equivalent(tmp_path: Path) -> None:
    fixture = json.loads(_golden_dataset_path().read_text(encoding="utf-8"))
    request_payload = fixture["request"]
    expected = fixture["expected"]

    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(request_payload), encoding="utf-8")

    cli_runner = CliRunner()
    cli_result = cli_runner.invoke(app, ["close-month", "--input", str(input_file)])
    assert cli_result.exit_code == 0

    skill_result = handle_command(f"fechar {json.dumps(request_payload)}")

    cli_summary = _parse_cli_summary(cli_result.stdout)
    skill_summary = _parse_skill_summary(skill_result)

    assert cli_summary["payer_external_id"] == skill_summary["payer_external_id"]
    assert cli_summary["receiver_external_id"] == skill_summary["receiver_external_id"]
    assert cli_summary["amount_brl"] == skill_summary["amount_brl"]
    assert cli_summary["counts"] == skill_summary["counts"]

    expected_transfer = expected["transfer_instruction"]
    assert cli_summary["payer_external_id"] == expected_transfer["payer_external_id"]
    assert (
        cli_summary["receiver_external_id"] == expected_transfer["receiver_external_id"]
    )
    assert cli_summary["amount_brl"] == expected_transfer["amount_brl"]
    assert cli_summary["counts"] == expected["counts"]

    report = CloseMonthUseCase().execute(
        CloseMonthRequest.model_validate(request_payload)
    )
    assert report.transfer_instruction.amount_brl == str(cli_summary["amount_brl"])
    assert report.counts.model_dump() == cli_summary["counts"]
