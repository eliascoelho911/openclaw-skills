"""CLI commands for compras_divididas."""

import typer

app = typer.Typer(help="Compras Divididas command line tools")


@app.command()
def healthcheck() -> None:
    """Run lightweight readiness check."""

    typer.echo("compras-divididas is ready")


if __name__ == "__main__":
    app()
