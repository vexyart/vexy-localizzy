# this_file: src/vexy_localizzy/cli_tm.py
"""Fire-ready ``localizzy tm`` subcommands: legacy converters and strict extraction.

Each function mirrors ``run`` in ``vexy_localizzy.extract.<module>`` and imports
it on call, so the CLI loads without the optional ``sources`` extra. Commands
return plain dicts; the legacy converters raise ``SystemExit`` on failure as
their fl10n scripts did.
"""

from importlib import import_module
from pathlib import Path

from vexy_localizzy.source_extraction import extract


def _run(module: str, *args: object, **kwargs: object) -> dict:
    return import_module(f"vexy_localizzy.extract.{module}").run(*args, **kwargs)


def ts2tmx(
    input: str,
    output: str | None = None,
    src_lang: str | None = None,
    verbose: bool = False,
) -> dict:
    """Convert one .ts file or every .ts under a folder to TMX (legacy language policy).

    Args:
        input: a ``.ts`` file or a directory searched recursively.
        output: ``.tmx`` path for a file input; mirrored output folder for a directory.
        src_lang: language of ``<source>`` text (default: ``sourcelanguage``, else ``en``).
        verbose: debug logging.
    """
    return _run("ts2tmx", input, output, src_lang, verbose)


def po2tmx(
    input: str,
    output: str | None = None,
    src_lang: str = "en",
    fuzzy: bool = False,
    verbose: bool = False,
) -> dict:
    """Convert one .po file or every .po under a folder to TMX (legacy language policy).

    Args:
        input: a ``.po`` file or a directory searched recursively.
        output: ``.tmx`` path for a file input; mirrored output folder for a directory.
        src_lang: language of ``msgid`` text.
        fuzzy: include entries flagged fuzzy.
        verbose: debug logging.
    """
    return _run("po2tmx", input, output, src_lang, fuzzy, verbose)


def lproj2tmx(
    app: str,
    output: str,
    dedupe: bool = True,
    skip_identical: bool = False,
    include_infoplist: bool = False,
    verbose: bool = False,
) -> dict:
    """Convert an .app bundle's .lproj/.strings and .loctable files into per-language TMX.

    Args:
        app: bundle folder.
        output: folder that receives <lang>.tmx files.
        dedupe: collapse identical (source, target) pairs within a language.
        skip_identical: drop units whose target equals the English source.
        include_infoplist: also read InfoPlist bundle metadata tables.
        verbose: debug logging.
    """
    return _run(
        "lproj", app, output, dedupe, skip_identical, include_infoplist, verbose
    )


def adobe2tmx(
    input: str,
    output: str,
    ui_lang: str | None = None,
    dedupe: bool = True,
    skip_identical: bool = False,
    include_infoplist: bool = False,
    verbose: bool = False,
) -> dict:
    """Convert an Adobe app folder's localization resources into per-language TMX.

    Args:
        input: app folder.
        output: folder that receives <lang>.tmx files.
        ui_lang: language of ZStrings inside binaries; auto-detected when omitted.
        dedupe: collapse identical (source, target) pairs within a language.
        skip_identical: drop units whose target equals the English source.
        include_infoplist: also read InfoPlist.strings bundle metadata.
        verbose: debug logging.
    """
    return _run(
        "adobe",
        input,
        output,
        ui_lang,
        dedupe,
        skip_identical,
        include_infoplist,
        verbose,
    )


def oss2tmx(
    output: str,
    apps: str | tuple[str, ...] | None = None,
    registry: str | None = None,
    cache: str | None = None,
    refresh: bool = False,
    verbose: bool = False,
) -> dict:
    """Fetch upstream translations of open-source apps and write <app>/<lang>.tmx.

    Args:
        output: folder receiving <app>/<lang>.tmx.
        apps: comma-separated subset of app names; default all.
        registry: TOML app registry replacing the packaged oss_apps.toml.
        cache: where git checkouts live (default: <output>/_src).
        refresh: re-clone repositories even if cached.
        verbose: debug logging.
    """
    return _run("oss", output, apps, registry, cache, refresh, verbose)


def norm(input: str, dry_run: bool = False, verbose: bool = False) -> dict:
    """Rename every .tmx under a folder to its shortest BCP 47 tag (legacy tmxnorm).

    Args:
        input: folder searched recursively.
        dry_run: report only, rename nothing.
        verbose: debug logging.
    """
    return import_module("vexy_localizzy.extract.names").norm(input, dry_run, verbose)


def build_ui(
    catalog: str,
    out: str,
    lang: str | None = None,
    exclude_memory: str | None = None,
    note: str | None = None,
) -> dict:
    """Build a project memory (every finished message) from a Qt .ts catalog.

    --exclude-memory a.tmx,b.tmx drops sources that are whole glossary terms,
    so the project memory never repeats the core memory. --lang overrides the
    memory's target tag (for example es-419 for an es_MX catalog).
    """
    from vexy_localizzy.cli_args import csv_paths
    from vexy_localizzy.memory.build_ui import build_ui as _build_ui

    return _build_ui(
        Path(str(catalog)),
        Path(str(out)),
        lang=str(lang) if lang else None,
        exclude_memories=csv_paths(exclude_memory),
        note=str(note) if note else None,
    )


TM_COMMANDS = {
    "build_ui": build_ui,
    "ts2tmx": ts2tmx,
    "po2tmx": po2tmx,
    "lproj2tmx": lproj2tmx,
    "adobe2tmx": adobe2tmx,
    "oss2tmx": oss2tmx,
    "norm": norm,
    "extract": extract,
}
