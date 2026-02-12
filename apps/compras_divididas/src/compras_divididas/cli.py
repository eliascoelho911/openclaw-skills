"""CLI commands for compras_divididas."""

from __future__ import annotations

from typing import Annotated

import typer

app = typer.Typer(help="Compras Divididas command line tools")


@app.command()
def healthcheck() -> None:
    """Run lightweight readiness check."""

    typer.echo("compras-divididas is ready")


@app.command("mcp")
def run_mcp_server(
    api_base_url: Annotated[
        str | None,
        typer.Option(
            "--api-base-url",
            help="Override API base URL used by MCP tools.",
        ),
    ] = None,
    timeout_seconds: Annotated[
        float | None,
        typer.Option(
            "--timeout-seconds",
            min=0.1,
            help="HTTP timeout in seconds for MCP tool calls.",
        ),
    ] = None,
) -> None:
    """Run MCP server over stdio transport."""

    from compras_divididas.mcp.server import create_mcp_server

    mcp_server = create_mcp_server(
        api_base_url=api_base_url,
        timeout_seconds=timeout_seconds,
    )
    mcp_server.run()


if __name__ == "__main__":
    app()
