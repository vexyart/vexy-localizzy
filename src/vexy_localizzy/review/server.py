# this_file: src/vexy_localizzy/review/server.py
"""Configured loopback server for the packaged review application."""

import json
import tomllib
from pathlib import Path

from pydantic import Field

from vexy_localizzy.catalog import Record
from vexy_localizzy.qa.text import TextPolicy
from vexy_localizzy.review.api import create_app
from vexy_localizzy.review.store import ReviewStore

# Built review frontend shipped as package data (``npm run build`` in review/).
WEB_ROOT = Path(__file__).with_name("web")
BROWSER_DELAY = 0.8  # seconds; lets the server bind before the browser asks


class ReviewConfig(Record):
    root: str = "."
    catalogs: dict[str, str]
    ui_files: dict[str, str] = Field(default_factory=dict)
    plural_forms: dict[str, list[str]] = Field(default_factory=dict)
    policies: dict[str, TextPolicy] = Field(default_factory=dict)
    suggestions: str | None = None


def load_app(config, *, web_root=None):
    path = Path(config).resolve(strict=True)
    settings = ReviewConfig.model_validate(tomllib.loads(path.read_text()))
    root = (path.parent / settings.root).resolve(strict=True)
    store = ReviewStore(
        root,
        settings.catalogs,
        policies=settings.policies,
        plural_forms=settings.plural_forms,
    )
    examples = {}
    if settings.suggestions:
        source = (root / settings.suggestions).resolve(strict=True)
        if not source.is_relative_to(root):
            raise ValueError("Suggestions must stay inside the review root")
        examples = json.loads(source.read_text())

    def suggestions(catalog_id, unit):
        return examples.get(catalog_id, {}).get(unit.key, [])

    return create_app(
        store, ui_files=settings.ui_files, suggestions=suggestions, web_root=web_root
    )


def serve(
    config: str,
    port: int = 8765,
    verbose: bool = False,
    workspace: str | None = None,
    ui_files: tuple[str, ...] = (),
    open_browser: bool = False,
):
    """Run the review UI/API on loopback.

    CONFIG is a review TOML, or a ``.ts``/``.json`` catalog that is imported
    into a resumable workspace first (``workspace`` and ``ui_files`` apply to
    that import only). The port range is validated before any workspace is created.
    """
    import uvicorn

    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Port must be from 1 through 65535")
    web = WEB_ROOT
    if not (web / "index.html").is_file():
        raise RuntimeError(
            "Review frontend is missing; run npm ci and npm run build in review/"
        )
    if Path(config).suffix.lower() != ".toml":
        from vexy_localizzy.review.workspace import prepare_workspace

        config = str(prepare_workspace(config, workspace=workspace, ui_files=ui_files))
    elif workspace is not None or ui_files:
        raise ValueError("Configure the workspace and UI files inside the review TOML")
    timer = None
    if open_browser:
        import threading
        import webbrowser

        timer = threading.Timer(
            BROWSER_DELAY, lambda: webbrowser.open(f"http://127.0.0.1:{port}")
        )
        timer.start()
    try:
        uvicorn.run(
            load_app(config, web_root=web),
            host="127.0.0.1",
            port=port,
            log_level="debug" if verbose else "warning",
        )
    finally:
        if timer is not None:
            timer.cancel()
