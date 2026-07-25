"""The ``mdreview`` command line interface."""

from __future__ import annotations

import os
import webbrowser
from pathlib import Path
from typing import Annotated

import typer

from . import __version__, config
from .client import ApiError, ApiUnreachable, Client
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


def _fail(message: str, code: Exit) -> typer.Exit:
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    return typer.Exit(code)


@app.command()
def submit(
    path: Annotated[Path, typer.Argument(help="Markdown file to publish for review.")],
    slug: Annotated[
        str | None, typer.Option("--slug", help="Reuse an existing document slug.")
    ] = None,
    title: Annotated[
        str | None, typer.Option("--title", help="Title shown on the review page.")
    ] = None,
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Open the review page.")
    ] = True,
    as_json: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
    host: HostOption = None,
    port: PortOption = None,
) -> None:
    """Publish a markdown file for review and print its URL."""
    if not path.is_file():
        raise _fail(f"no such file: {path}", Exit.ERROR)

    content = path.read_text(encoding="utf-8")
    settings = _settings(host, port)

    with Client(settings) as client:
        try:
            result = client.post(
                "/api/documents",
                json={
                    "content": content,
                    "slug": slug,
                    "title": title,
                    "project_path": str(Path.cwd()),
                    "session_id": os.environ.get("MDREVIEW_SESSION_ID"),
                    "source_name": path.stem,
                },
            )
        except ApiUnreachable as exc:
            raise _fail(str(exc), Exit.UNREACHABLE) from exc
        except ApiError as exc:
            raise _fail(exc.detail, Exit.ERROR) from exc

    if as_json:
        import json

        typer.echo(json.dumps(result, indent=2))
    else:
        note = " (unchanged, reusing existing round)" if result["reused"] else ""
        typer.echo(f"{result['slug']} v{result['version']}{note}")
        typer.echo(result["url"])

    if open_browser:
        webbrowser.open(result["url"])


@app.command("open")
def open_document(
    slug: Annotated[str, typer.Argument(help="Document slug.")],
    host: HostOption = None,
    port: PortOption = None,
) -> None:
    """Open a document's review page in the browser."""
    settings = _settings(host, port)
    with Client(settings) as client:
        try:
            document = client.get(f"/api/documents/{slug}")
        except ApiUnreachable as exc:
            raise _fail(str(exc), Exit.UNREACHABLE) from exc
        except ApiError as exc:
            raise _fail(exc.detail, Exit.ERROR) from exc
    webbrowser.open(document["url"])
    typer.echo(document["url"])
