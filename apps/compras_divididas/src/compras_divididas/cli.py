"""CLI bootstrap for compras-divididas."""

import json
from pathlib import Path

import typer

from compras_divididas.application.use_cases.close_month import (
    CloseMonthRequest,
    CloseMonthUseCase,
)

app = typer.Typer(help="CLI for monthly shared-purchase reconciliation.")
INPUT_FILE_OPTION = typer.Option(..., exists=True, dir_okay=False)


@app.command("healthcheck")
def healthcheck() -> None:
    """Verify that the CLI entrypoint is available."""
    typer.echo("compras-divididas is ready")


@app.command("close-month")
def close_month(input: Path = INPUT_FILE_OPTION) -> None:
    """Process a monthly closure from a JSON input file."""
    payload = json.loads(input.read_text(encoding="utf-8"))
    request = CloseMonthRequest.model_validate(payload)
    report = CloseMonthUseCase().execute(request)

    transfer = report.transfer_instruction
    typer.echo(f"Fechamento {report.period.year:04d}-{report.period.month:02d}")
    typer.echo(f"Pagador: {transfer.payer_external_id or '-'}")
    typer.echo(f"Recebedor: {transfer.receiver_external_id or '-'}")
    typer.echo(f"Valor: {transfer.amount_brl}")
    typer.echo(
        "Validos: "
        f"{report.counts.valid} | "
        f"Invalidos: {report.counts.invalid} | "
        f"Ignorados: {report.counts.ignored} | "
        f"Deduplicados: {report.counts.deduplicated}"
    )


def main() -> None:
    """Run the compras-divididas CLI application."""
    app()


if __name__ == "__main__":
    main()
