"""Allow ``python -m mdreview`` so autostart does not depend on PATH."""

from .cli import app

if __name__ == "__main__":
    app()
