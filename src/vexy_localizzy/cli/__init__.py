# this_file: src/vexy_localizzy/cli/__init__.py
"""Command-line entry points for generic catalog workflows.

The ``translate``, ``upgrade``, ``checks``, ``editorial``, ``project``, ``qt``,
``tm`` and ``utilities`` submodules hold the bigger commands.
This module never binds those names itself, so ``vexy_localizzy.cli.translate``
stays the submodule and dotted paths such as ``vexy_localizzy.cli.translate.translate``
resolve for imports and monkeypatching.
"""

import sys
from pathlib import Path
from subprocess import SubprocessError

import fire
from loguru import logger

from vexy_localizzy.cli import checks as _checks
from vexy_localizzy.cli import editorial as _editorial
from vexy_localizzy.cli import project as _project
from vexy_localizzy.cli import qt as _qt
from vexy_localizzy.cli import sourcefix as _sourcefix
from vexy_localizzy.cli import tm as _tm
from vexy_localizzy.cli import translate as _translate
from vexy_localizzy.cli import upgrade as _upgrade
from vexy_localizzy.cli import utilities as _utilities
from vexy_localizzy.conversion import convert as convert_catalog
from vexy_localizzy.external import MissingDependencyError
from vexy_localizzy.inventory import write_inventory

EXIT_USAGE, EXIT_DEPENDENCY, EXIT_INTERRUPTED = 2, 3, 130
# What a wrong path, a malformed file or a failing external tool raises.
# ValueError covers pydantic validation and TOML decoding errors.
INPUT_ERRORS = (OSError, ValueError, RuntimeError, SyntaxError, SubprocessError)


def inventory(root: str, output: str, verbose: bool = False) -> dict:
    """Inventory all .tmx and .ts XML catalogs recursively under ROOT."""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "WARNING")
    directory = Path(root).resolve()
    if not directory.is_dir():
        raise ValueError(f"Input directory does not exist: {directory}")
    paths = sorted(
        path
        for path in directory.rglob("*")
        if path.suffix.lower() in {".tmx", ".ts"} and path.is_file()
    )
    return write_inventory(paths, Path(output), root=directory)


def convert(
    src: str,
    target: str,
    out: str,
    allow_loss: bool = False,
    plural_forms: str | None = None,
    plural_order: list[str] | None = None,
    source_format: str | None = None,
    source_lang: str | None = None,
    target_lang: str | None = None,
) -> dict:
    """Convert catalogs; use source_format=i18next for application JSON."""
    result = convert_catalog(
        src,
        target,
        out,
        allow_loss=allow_loss,
        plural_forms=plural_forms,
        plural_order=plural_order,
        source_format=source_format,
        source_lang=source_lang,
        target_lang=target_lang,
    )
    return {
        "output": str(result.out_path),
        "entries": len(result.catalog.units),
        "findings": [finding.model_dump() for finding in result.findings],
    }


def review(
    config: str,
    port: int = 8765,
    verbose: bool = False,
    workspace: str | None = None,
    ui_files: str | None = None,
    open_browser: bool = False,
):
    """Serve catalogs with the optional review UI and API.

    CONFIG is a review TOML, or a .ts/.json catalog that is first imported into
    a resumable workspace (default CONFIG.review; --workspace overrides it and
    --ui-files a.ui,b.ui adds form previews). The source catalog is never edited.
    """
    from vexy_localizzy.cli._args import csv_strings
    from vexy_localizzy.review.server import serve

    return serve(
        config,
        port=port,
        verbose=verbose,
        workspace=workspace,
        ui_files=tuple(csv_strings(ui_files)),
        open_browser=open_browser,
    )


COMMANDS = {
    "source-fix": _sourcefix.COMMANDS,
    "translate": _translate.translate,
    "upgrade": _upgrade.upgrade,
    "convert": convert,
    "qa": _checks.qa,
    "pseudo": _checks.pseudo,
    "review": review,
    "inventory": inventory,
    "vocab": _checks.vocab,
    "doctor": _checks.doctor,
    "init": _checks.init,
    "diff": _utilities.diff,
    "shard": _utilities.UTILITY_COMMANDS["shard"],
    "translate_json": _utilities.translate_json,
    "editorial": _editorial.EDITORIAL_COMMANDS,
    "project": _project.PROJECT_COMMANDS,
    "qt": _qt.QT_COMMANDS,
    "tm": _tm.TM_COMMANDS,
}


def main() -> None:
    """Expose explicit subcommands through Python Fire; exit 2 on bad input.

    Hot-path verbs sit at the top level. Memory builders and converters are
    grouped under ``tm``, Qt tooling under ``qt`` and the commands that read
    ``localizzy.toml`` under ``project``.
    """
    try:
        fire.Fire(COMMANDS)
    except KeyboardInterrupt:
        raise SystemExit(EXIT_INTERRUPTED) from None
    except MissingDependencyError as error:
        print(f"localizzy: {error}", file=sys.stderr)
        raise SystemExit(EXIT_DEPENDENCY) from error
    except INPUT_ERRORS as error:
        # Bad input is the user's to fix: one line and exit 2, never a traceback.
        print(f"localizzy: {error}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE) from error
