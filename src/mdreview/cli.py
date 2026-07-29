"""The ``mdreview`` command line interface."""

from __future__ import annotations

import json
import os
import webbrowser
from pathlib import Path
from typing import Annotated, Any

import typer

from . import __version__, config, report, session
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
    str | None,
    typer.Option("--host", help="Address to bind or connect to, or 'auto' to discover it."),
]
PortOption = Annotated[int | None, typer.Option("--port", help="Port to bind or connect to.")]
AllowLanOption = Annotated[
    bool,
    typer.Option(
        "--allow-lan",
        help="Allow an unauthenticated bind to one private LAN address.",
    ),
]


def _settings(host: str | None, port: int | None, allow_lan: bool = False) -> Settings:
    from . import net

    try:
        # Resolved before Settings.load validates it, so discovery is incapable of
        # widening what may be bound.
        host = net.resolve_host(host)
    except net.NoLanAddress as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(Exit.ERROR) from exc

    try:
        return Settings.load(host=host, port=port, allow_lan=allow_lan)
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
    allow_lan: AllowLanOption = False,
    foreground: Annotated[
        bool,
        typer.Option("--foreground/--detach", help="Run attached to this terminal."),
    ] = True,
) -> None:
    """Run the review server."""
    from . import server

    settings = _settings(host, port, allow_lan)
    if not config.is_loopback(settings.host):
        from . import tokens

        entry = f"{settings.base_url}/?{tokens.QUERY_PARAM}={tokens.ensure()}"
        typer.secho(
            "warning: reviews are exposed on the network. Open this link to "
            "authorise a device; anyone holding it can read and change reviews:",
            fg=typer.colors.YELLOW,
            err=True,
        )
        typer.secho(entry, fg=typer.colors.YELLOW, err=True)
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
    allow_lan: AllowLanOption = False,
) -> None:
    """Publish a markdown file for review and print its URL."""
    if not path.is_file():
        raise _fail(f"no such file: {path}", Exit.ERROR)

    content = path.read_text(encoding="utf-8")
    settings = _settings(host, port, allow_lan)

    # Detected at submit time, not at import: Claude Code rewrites its
    # session id in place after a conversation reset.
    origin = session.detect(os.environ)

    with Client(settings) as client:
        try:
            result = client.post(
                "/api/documents",
                json={
                    "content": content,
                    "slug": slug,
                    "title": title,
                    "project_path": str(Path.cwd()),
                    "session_id": origin.session_id,
                    "session_tool": origin.tool,
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
    allow_lan: AllowLanOption = False,
) -> None:
    """Open a document's review page in the browser."""
    settings = _settings(host, port, allow_lan)
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
    allow_lan: AllowLanOption = False,
) -> None:
    """Read the review outcome. The exit code carries the result.

    0 approved, 2 changes requested, 3 not yet decided, 4 cancelled,
    5 the API could not be reached.
    """
    settings = _settings(host, port, allow_lan)
    with Client(settings) as client:
        state = _state(client, slug)
        _warn_on_version_skew(client)

    status = ReviewStatus(state["status"])
    if as_json:
        typer.echo(json.dumps(state, indent=2))
    else:
        typer.echo(report.render_state(state))

    raise typer.Exit(exit_for(status))


@app.command("await")
def await_decision(
    slug: Annotated[str, typer.Argument(help="Document slug.")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Give up after this many seconds, exiting 3."),
    ] = 8 * 60 * 60,
    host: HostOption = None,
    port: PortOption = None,
    allow_lan: AllowLanOption = False,
) -> None:
    """Wait until the latest version is decided, then report like `review`.

    Built to run as a background task: the process ending is the
    notification, and the exit code is the message — the same mapping as
    `review`. The wait is a client-side poll; the server holds no
    connection and does not know it is being watched.
    """
    import time

    interval = 2.0
    # Sixty consecutive unreachable seconds end the wait: brief restarts
    # (upgrades, autostart races) are ridden out, a dead server is not an
    # outcome. Capped by the timeout so a short --timeout stays short.
    unreachable_grace = min(60.0, timeout)

    settings = _settings(host, port, allow_lan)
    deadline = time.monotonic() + timeout
    unreachable_since: float | None = None
    reached = False
    state: dict[str, Any] | None = None

    typer.secho(
        f"awaiting a decision on {slug!r} (polling every {interval:g}s, timeout {timeout:g}s)",
        fg=typer.colors.BLUE,
        err=True,
    )

    with Client(settings) as client:
        while True:
            try:
                state = client.get(f"/api/documents/{slug}/state")
            except ApiUnreachable as exc:
                now = time.monotonic()
                unreachable_since = unreachable_since or now
                if now - unreachable_since >= unreachable_grace:
                    raise _fail(str(exc), Exit.UNREACHABLE) from exc
            except ApiError as exc:
                raise _fail(exc.detail, Exit.ERROR) from exc
            else:
                reached = True
                unreachable_since = None
                status = ReviewStatus(state["status"])
                if status.is_decided:
                    typer.echo(report.render_state(state))
                    raise typer.Exit(exit_for(status))

            if time.monotonic() >= deadline:
                break
            time.sleep(interval)

    if not reached:
        # Never got an answer: "undecided" is a statement about the review,
        # and an unreachable server cannot make it.
        raise _fail("server was never reachable while waiting", Exit.UNREACHABLE)
    assert state is not None
    typer.echo(report.render_state(state))
    raise typer.Exit(exit_for(ReviewStatus(state["status"])))


@app.command()
def status(
    slug: Annotated[str, typer.Argument(help="Document slug.")],
    host: HostOption = None,
    port: PortOption = None,
    allow_lan: AllowLanOption = False,
) -> None:
    """Print one line describing where a document stands."""
    settings = _settings(host, port, allow_lan)
    with Client(settings) as client:
        state = _state(client, slug)
    typer.echo(
        report.header(
            ReviewStatus(state["status"]),
            state["version"],
            len(state.get("open_comments") or []),
        )
    )


@app.command()
def delete(
    slug: Annotated[str, typer.Argument(help="Document slug.")],
    yes: Annotated[bool, typer.Option("--yes", help="Skip the confirmation prompt.")] = False,
    host: HostOption = None,
    port: PortOption = None,
    allow_lan: AllowLanOption = False,
) -> None:
    """Permanently remove a document, its versions, and their comments.

    For putting a document away without destroying it, use Archive on the
    review index instead.
    """
    settings = _settings(host, port, allow_lan)
    with Client(settings) as client:
        try:
            document = client.get(f"/api/documents/{slug}")
        except ApiUnreachable as exc:
            raise _fail(str(exc), Exit.UNREACHABLE) from exc
        except ApiError as exc:
            raise _fail(exc.detail, Exit.ERROR) from exc

        versions = len(document.get("versions") or [])
        if not yes and not typer.confirm(
            f"Permanently delete {slug!r} ({versions} version"
            f"{'s' if versions != 1 else ''}, all comments)? This cannot be undone."
        ):
            # Declining is a successful non-action, not a failure.
            typer.echo("nothing deleted")
            raise typer.Exit(Exit.OK)
        try:
            client.delete(f"/api/documents/{slug}")
        except ApiUnreachable as exc:
            raise _fail(str(exc), Exit.UNREACHABLE) from exc
        except ApiError as exc:
            raise _fail(exc.detail, Exit.ERROR) from exc

    typer.echo(f"deleted {slug}")


@app.command("list")
def list_documents(
    pending: Annotated[
        bool, typer.Option("--pending", help="Only documents awaiting a decision.")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
    host: HostOption = None,
    port: PortOption = None,
    allow_lan: AllowLanOption = False,
) -> None:
    """List submitted documents."""
    settings = _settings(host, port, allow_lan)
    with Client(settings) as client:
        try:
            items = client.get("/api/documents", params={"pending": pending})
        except ApiUnreachable as exc:
            raise _fail(str(exc), Exit.UNREACHABLE) from exc
        except ApiError as exc:
            raise _fail(exc.detail, Exit.ERROR) from exc

    typer.echo(json.dumps(items, indent=2) if as_json else report.render_list(items))


@app.command("lan-address")
def lan_address() -> None:
    """Print the private address that `--host auto` would choose."""
    from . import net

    try:
        typer.echo(net.detect())
    except net.NoLanAddress as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(Exit.ERROR) from exc
