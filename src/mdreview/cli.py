"""The ``mdreview`` command line interface."""

from __future__ import annotations

from typing import Annotated

import typer

from . import __version__, config
from .config import Settings
from .exits import Exit

app = typer.Typer(
    name="mdreview",
    help="Review agent-authored markdown in a browser instead of a text editor.",
    add_completion=False,
    no_args_is_help=True,
)

HostOption = Annotated[
    str | None, typer.Option("--host", help="Loopback address to bind or connect to.")
]
PortOption = Annotated[int | None, typer.Option("--port", help="Port to bind or connect to.")]


def _settings(host: str | None, port: int | None) -> Settings:
    try:
        return Settings.load(host=host, port=port)
    except ValueError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(Exit.ERROR) from exc


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"mdreview {__version__}")
        raise typer.Exit(Exit.OK)


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Review agent-authored markdown in a browser instead of a text editor."""


@app.command()
def serve(
    host: HostOption = None,
    port: PortOption = None,
    foreground: Annotated[
        bool,
        typer.Option("--foreground/--detach", help="Run attached to this terminal."),
    ] = True,
) -> None:
    """Run the review server."""
    from . import server

    settings = _settings(host, port)
    if not foreground:
        from .client import Client

        with Client(settings) as client:
            try:
                client.ensure_up()
            except Exception as exc:
                typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
                raise typer.Exit(Exit.UNREACHABLE) from exc
        typer.echo(f"mdreview serving at {settings.base_url}")
        return

    typer.echo(f"mdreview {__version__} serving at {settings.base_url}", err=True)
    typer.echo(f"database: {settings.database}", err=True)
    server.run(settings, log_file=config.log_path())
