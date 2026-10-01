# this_file: src/vexy_localizzy/qt/lupdate.py
"""Extract Qt sources into TS catalogs with the native ``lupdate``.

Extraction must use Qt's own parser, never artifact scraping, so a missing
``lupdate`` raises ``MissingDependencyError``. ``.pro`` inputs are passed
through so only files the project compiles are extracted.

Existing catalogs are merged, not overwritten: lupdate runs on hidden copies
next to them, and each real file is replaced only after lupdate succeeded,
every output parsed and the source catalog still has live messages. Strings
that left the source stay in the catalogs as vanished, with their
translations, unless ``no_obsolete`` is set.
"""

import re
import secrets
from pathlib import Path

from vexy_localizzy.catalog import Catalog
from vexy_localizzy.external import require_tool
from vexy_localizzy.formats import ts as ts_io
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.qt.process import run_tool

# Seconds; large projects take minutes, but a hung lupdate must not stall forever.
LUPDATE_TIMEOUT = 1800
LOCATIONS = ("none", "relative", "absolute")
DEFAULT_EXTENSIONS = "cpp,h,cc,cxx,ui"
_TOKEN_BYTES = 6


def ts_path(out_dir: Path, prefix: str, locale: str) -> Path:
    """Return ``{out_dir}/{prefix}_{locale}.ts``."""
    return Path(out_dir) / f"{prefix}_{locale}.ts"


def _lupdate_cwd(sources: list[Path]) -> Path:
    """Run from the first ``.pro``'s directory so relative INCLUDEPATH entries work."""
    first = sources[0]
    return first.parent if first.is_file() else first


def _source_args(sources: list[Path]) -> list[str]:
    """``.pro`` files as-is; directories with a nested ``src`` add it as include path."""
    args: list[str] = []
    for src in sources:
        if src.suffix != ".pro" and (src / "src").is_dir():
            args += ["-I", str(src / "src")]
        args.append(str(src))
    return args


def command(
    tool: str,
    sources: list[Path],
    ts_files: list[Path],
    *,
    locations: str,
    extensions: str,
    no_obsolete: bool = False,
) -> list[str]:
    """The ``lupdate`` command line; ``no_obsolete`` drops strings that left the source."""
    cmd = [tool, "-locations", locations, "-extensions", extensions]
    if no_obsolete:
        cmd.append("-no-obsolete")
    cmd += _source_args(sources)
    for ts in ts_files:
        cmd += ["-ts", str(ts)]
    return cmd


def _base(language: str | None) -> str:
    return re.split(r"[_-]", language or "")[0].lower()


def _check(sources: list[Path], prefix: str | None, locations: str) -> None:
    if not sources:
        raise ValueError("lupdate needs at least one source directory or .pro file")
    if missing := [str(s) for s in sources if not Path(s).exists()]:
        raise ValueError(f"source path(s) not found: {', '.join(missing)}")
    if not (prefix or "").strip():
        raise ValueError("prefix must name the catalogs, e.g. 'myapp' for myapp_de.ts")
    if locations not in LOCATIONS:
        raise ValueError(f"locations must be one of {', '.join(LOCATIONS)}")


def _read_output(work: Path, locale: str, source_lang: str) -> Catalog:
    """Parse one lupdate output; give a locale catalog its language if it lacks it."""
    if not work.is_file():
        raise RuntimeError(f"lupdate did not write {work}")
    catalog = ts_io.load(work)
    if locale != source_lang and _base(catalog.target_lang) != _base(locale):
        catalog = catalog.model_copy(update={"target_lang": locale})
        ts_io.dump(catalog, work)
    return catalog


def run(
    sources: list[Path],
    out_dir: Path,
    *,
    prefix: str,
    locales: list[str] | None = None,
    locations: str = "none",
    source_lang: str = "en",
    extensions: str = DEFAULT_EXTENSIONS,
    no_obsolete: bool = False,
) -> dict[str, Catalog]:
    """Extract ``sources`` (directories or ``.pro`` files) to ``{prefix}_{locale}.ts``.

    Returns one Catalog per locale, source language first. Raises
    ``ValueError`` for bad arguments or missing sources,
    ``MissingDependencyError`` without ``lupdate`` and ``RuntimeError`` when
    ``lupdate`` fails, times out or finds no messages; in each of those cases
    no catalog is replaced.
    """
    _check(sources, prefix, locations)
    tool = require_tool("lupdate")
    resolved = [Path(s).resolve() for s in sources]
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ordered = [source_lang] + [loc for loc in locales or [] if loc != source_lang]
    finals = [ts_path(out_dir, prefix, loc) for loc in ordered]
    # Hidden siblings keep relative locations and lupdate's language guess intact.
    token = secrets.token_hex(_TOKEN_BYTES)
    works = [out_dir / f".{token}.{final.name}" for final in finals]
    try:
        for final, work in zip(finals, works, strict=True):
            if final.is_file():
                work.write_bytes(final.read_bytes())
        cmd = command(
            tool,
            resolved,
            works,
            locations=locations,
            extensions=extensions,
            no_obsolete=no_obsolete,
        )
        run_tool("lupdate", cmd, timeout=LUPDATE_TIMEOUT, cwd=_lupdate_cwd(resolved))
        catalogs = {
            loc: _read_output(work, loc, source_lang)
            for loc, work in zip(ordered, works, strict=True)
        }
        if not any(u.state != "vanished" for u in catalogs[source_lang].units):
            raise RuntimeError(
                f"lupdate found no messages in {', '.join(map(str, resolved))}; no catalog was changed"
            )
        for final, work in zip(finals, works, strict=True):
            atomic_write(final, work.read_bytes())
    finally:
        for work in works:
            work.unlink(missing_ok=True)
    return catalogs
