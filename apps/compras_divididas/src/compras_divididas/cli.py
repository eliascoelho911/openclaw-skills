"""CLI bootstrap for compras-divididas."""

import typer

app = typer.Typer(help="CLI for monthly shared-purchase reconciliation.")


@app.command("healthcheck")
def healthcheck() -> None:
    """Verify that the CLI entrypoint is available."""
    typer.echo("compras-divididas is ready")


def main() -> None:
    """Run the compras-divididas CLI application."""
    app()


if __name__ == "__main__":
    main()
