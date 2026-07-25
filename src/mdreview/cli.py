"""The ``mdreview`` command line interface."""

from __future__ import annotations

import json
import os
import webbrowser
from pathlib import Path
from typing import Annotated, Any

import typer

from . import __version__, config, report
from .client import ApiError, ApiUnreachable, Client
from .config import Settings
from .exits import Exit, exit_for
from .models import ReviewStatus

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


def _state(client: Client, slug: str) -> dict[str, Any]:
    try:
        return client.get(f"/api/documents/{slug}/state")
    except ApiUnreachable as exc:
        raise _fail(str(exc), Exit.UNREACHABLE) from exc
    except ApiError as exc:
        raise _fail(exc.detail, Exit.ERROR) from exc


def _warn_on_version_skew(client: Client) -> None:
    """A server left running across an upgrade will serve the old code."""
    running = client.server_version()
    if running is not None and running != __version__:
        typer.secho(
            f"warning: server is running {running} but this CLI is {__version__}; "
            f"restart it to pick up changes",
            fg=typer.colors.YELLOW,
            err=True,
        )


@app.command()
def review(
    slug: Annotated[str, typer.Argument(help="Document slug.")],
    as_json: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
    host: HostOption = None,
    port: PortOption = None,
) -> None:
    """Read the review outcome. The exit code carries the result.

    0 approved, 2 changes requested, 3 not yet decided, 4 cancelled,
    5 the API could not be reached.
    """
    settings = _settings(host, port)
    with Client(settings) as client:
        state = _state(client, slug)
        _warn_on_version_skew(client)

    status = ReviewStatus(state["status"])
    if as_json:
        typer.echo(json.dumps(state, indent=2))
    else:
        typer.echo(report.render_state(state))

    raise typer.Exit(exit_for(status))


@app.command()
def status(
    slug: Annotated[str, typer.Argument(help="Document slug.")],
    host: HostOption = None,
    port: PortOption = None,
) -> None:
    """Print one line describing where a document stands."""
    settings = _settings(host, port)
    with Client(settings) as client:
        state = _state(client, slug)
    typer.echo(
        report.header(
            ReviewStatus(state["status"]),
            state["version"],
            len(state.get("unresolved") or []),
        )
    )


@app.command()
def resolve(
    slug: Annotated[str, typer.Argument(help="Document slug.")],
    refs: Annotated[list[str], typer.Argument(help="Comment references, e.g. C1 C2.")],
    host: HostOption = None,
    port: PortOption = None,
) -> None:
    """Mark comments as addressed."""
    settings = _settings(host, port)
    with Client(settings) as client:
        state = _state(client, slug)
        try:
            result = client.post(
                f"/api/documents/{slug}/versions/{state['version']}/resolve",
                json={"refs": refs},
            )
        except ApiUnreachable as exc:
            raise _fail(str(exc), Exit.UNREACHABLE) from exc
        except ApiError as exc:
            raise _fail(exc.detail, Exit.ERROR) from exc

    typer.echo(
        f"resolved {', '.join(result['resolved'])} "
        f"({result['unresolved_remaining']} unresolved remaining)"
    )


@app.command("list")
def list_documents(
    pending: Annotated[
        bool, typer.Option("--pending", help="Only documents awaiting a decision.")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
    host: HostOption = None,
    port: PortOption = None,
) -> None:
    """List submitted documents."""
    settings = _settings(host, port)
    with Client(settings) as client:
        try:
            items = client.get("/api/documents", params={"pending": pending})
        except ApiUnreachable as exc:
            raise _fail(str(exc), Exit.UNREACHABLE) from exc
        except ApiError as exc:
            raise _fail(exc.detail, Exit.ERROR) from exc

    typer.echo(json.dumps(items, indent=2) if as_json else report.render_list(items))
