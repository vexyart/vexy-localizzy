# this_file: src/vexy_localizzy/cli/qt.py
"""``localizzy qt`` commands: scan Qt sources, run lupdate and lrelease, launch an app.

``scan`` and ``extract`` take source paths as arguments, or read ``[qt].sources``
from ``localizzy.toml`` when none is given. Findings are data; exit 1 means a
critical finding or coverage under the threshold, 2 a usage error and 3 a
missing tool or extra.
"""

import json
import sys
from pathlib import Path

from vexy_localizzy.cli._args import csv_strings
from vexy_localizzy.external import MissingDependencyError
from vexy_localizzy.project import Config, load_config

EXIT_FINDINGS, EXIT_USAGE, EXIT_DEPENDENCY = 1, 2, 3


def _fail(message: str, code: int) -> SystemExit:
    print(message, file=sys.stderr)
    return SystemExit(code)


def _sources(given: tuple[str, ...], config: str | None) -> tuple[list[Path], Config]:
    """The paths on the command line, else ``[qt].sources`` of the project file."""
    settings = load_config(config)
    paths = [Path(path) for path in given] or settings.qt_sources()
    if not paths:
        raise _fail(
            "Pass source paths, or list them under [qt].sources in localizzy.toml",
            EXIT_USAGE,
        )
    return paths, settings


def scan(
    *sources: str,
    engine: str = "heuristic",
    ui: bool = True,
    min_coverage: float | None = None,
    format: str = "table",
    out: str | None = None,
    compile_commands: str | None = None,
    config: str | None = None,
) -> None:
    """Audit Qt/C++ sources and .ui forms for strings that will not translate.

    --engine heuristic is a fast line pass; clang uses libclang (the ``clang``
    extra) and reads --compile-commands when given; both runs clang on files
    with critical heuristic findings. --format table, json or sarif. Exit 1 on
    a critical finding, or when coverage is below --min-coverage; --min-coverage
    over zero C++ files is a usage error (exit 2).
    """
    from vexy_localizzy import report
    from vexy_localizzy.qt import scan as scanner

    if format not in report.FORMATS:
        raise _fail(f"--format must be one of {', '.join(report.FORMATS)}", EXIT_USAGE)
    if out and not Path(out).resolve().parent.is_dir():
        raise _fail(f"--out directory does not exist: {Path(out).parent}", EXIT_USAGE)
    paths, _ = _sources(sources, config)
    try:
        result = scanner.run(
            paths,
            engine=engine,
            include_ui=ui,
            compile_commands=Path(compile_commands) if compile_commands else None,
        )
    except MissingDependencyError as error:
        raise _fail(str(error), EXIT_DEPENDENCY) from error
    except ValueError as error:
        raise _fail(str(error), EXIT_USAGE) from error
    if min_coverage is not None and not result.files:
        raise _fail(
            "--min-coverage needs at least one C++ file; none was scanned", EXIT_USAGE
        )
    try:
        _emit_scan(result, format, out)
    except OSError as error:
        raise _fail(f"cannot write {out}: {error}", EXIT_USAGE) from error
    if result.counts_by_severity["critical"]:
        raise SystemExit(EXIT_FINDINGS)
    if min_coverage is not None and result.overall_coverage < min_coverage:
        raise SystemExit(EXIT_FINDINGS)


def _emit_scan(result, format: str, out: str | None) -> None:
    """Print or write the scan in ``format``; JSON adds coverage per file."""
    from vexy_localizzy import report

    if format == "json":
        payload = {
            "sources": result.repos,
            "engine": result.engine,
            "overall_coverage": result.overall_coverage,
            "counts_by_severity": result.counts_by_severity,
            "files": [{**f.model_dump(), "coverage": f.coverage} for f in result.files],
            "findings": [finding.model_dump() for finding in result.findings],
        }
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        Path(out).write_text(text + "\n", encoding="utf-8") if out else print(text)
    else:
        report.emit(result.findings, format, out, title=f"scan ({result.engine})")
        if format == "table":
            print(
                f"overall coverage: {result.overall_coverage:.1%} "
                f"over {len(result.files)} file(s)"
            )


def extract(
    *sources: str,
    out_dir: str | None = None,
    locales: str | None = None,
    prefix: str | None = None,
    source_lang: str | None = None,
    locations: str = "none",
    no_obsolete: bool = False,
    config: str | None = None,
) -> dict:
    """Run Qt lupdate over source directories or .pro files into PREFIX_<locale>.ts.

    Existing catalogs are merged and replaced only after lupdate succeeds;
    strings that left the source stay as vanished with their translations.
    --no-obsolete drops translations of strings that left the source.
    --locales de,fr; the source-language catalog is always written.
    Unset options come from localizzy.toml ([qt] and [source]).
    """
    from vexy_localizzy.qt import lupdate

    paths, settings = _sources(sources, config)
    # lupdate runs from the source directory, so the output must be absolute.
    destination = (
        Path(out_dir).resolve() if out_dir else settings.resolve(settings.qt.out_dir)
    )
    name = prefix or settings.qt.prefix
    try:
        catalogs = lupdate.run(
            paths,
            destination,
            prefix=name,
            locales=csv_strings(locales) or list(settings.source.locales),
            locations=locations,
            source_lang=source_lang or settings.source.language,
            no_obsolete=no_obsolete,
        )
    except MissingDependencyError as error:
        raise _fail(str(error), EXIT_DEPENDENCY) from error
    except (ValueError, RuntimeError) as error:
        raise _fail(str(error), EXIT_USAGE) from error
    return {
        locale: {
            "units": len(catalog.units),
            "path": str(destination / f"{name}_{locale}.ts"),
        }
        for locale, catalog in catalogs.items()
    }


def release(*catalogs: str, out_dir: str | None = None) -> list[str]:
    """Compile .ts catalogs to .qm with Qt lrelease, beside each catalog or in --out-dir."""
    from vexy_localizzy.qt import lrelease

    if not catalogs:
        raise _fail(
            "usage: localizzy qt release CATALOG.ts [CATALOG.ts...]", EXIT_USAGE
        )
    try:
        written = lrelease.run(
            [Path(catalog) for catalog in catalogs],
            out_dir=Path(out_dir) if out_dir else None,
        )
    except MissingDependencyError as error:
        raise _fail(str(error), EXIT_DEPENDENCY) from error
    except (ValueError, RuntimeError) as error:
        raise _fail(str(error), EXIT_USAGE) from error
    return [str(path) for path in written]


def _applang(action: str, *args: object, **options: object):
    """Run one ``qt.applang`` function; bad input or a non-macOS host exits 2."""
    from vexy_localizzy.qt import applang

    try:
        return getattr(applang, action)(*args, **options)
    except (ValueError, RuntimeError) as error:
        raise _fail(str(error), EXIT_USAGE) from error


def applang_list(app: str, prefix: str, source_lang: str = "en") -> list[str]:
    """List the UI languages compiled into a macOS Qt app as PREFIX_<lang>.qm resources."""
    return _applang("languages", Path(app), prefix, source_language=source_lang)


def applang_run(app: str, lang: str, prefix: str, new: bool = False) -> None:
    """Launch a macOS Qt app in UI language LANG; --new starts a separate instance."""
    _applang("run", Path(app), lang, prefix, new=new)


def applang_write_commands(
    app: str, prefix: str, out: str, name: str | None = None
) -> list[str]:
    """Write one double-clickable <name>-<lang>.command launcher per UI language into OUT."""
    written = _applang("write_commands", Path(app), prefix, Path(out), name)
    return [str(path) for path in written]


QT_COMMANDS = {
    "scan": scan,
    "extract": extract,
    "release": release,
    "applang": {
        "list": applang_list,
        "run": applang_run,
        "write_commands": applang_write_commands,
    },
}
