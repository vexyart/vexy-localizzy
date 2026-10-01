# this_file: src/vexy_localizzy/extract/ts2tmx.py
"""Convert Qt Linguist ``.ts`` files, or a folder of them, to TMX 1.4.

Source language: ``src_lang``, else the ``sourcelanguage`` attribute, else
``en``. Target language: the ``<TS language>`` attribute, else the last dotted
or underscored part of the file stem (``scribus.de.ts``, ``app_pt_BR.ts``),
else the stem itself. Unfinished, obsolete and vanished translations are
skipped; numerus entries give a singular (first form) and a plural (last form)
unit; the context name lands in ``x-context``. Ported from the earlier ``ts2tmx`` script; see NOTICE.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from loguru import logger

from vexy_localizzy.extract.legacy_lang import norm_lang, stem_lang
from vexy_localizzy.extract.legacy_pairs import TS_SKIP_TYPES
from vexy_localizzy.extract.legacy_pairs import ts_pairs as units
from vexy_localizzy.extract.legacy_tmx import write_tmx
from vexy_localizzy.extract.walk import convert_all, plan_jobs

TOOL = "ts2tmx"
SKIP_TYPES = TS_SKIP_TYPES
__all__ = ["SKIP_TYPES", "TOOL", "convert", "run", "stem_lang", "target_lang", "units"]


def target_lang(root: ET.Element, path: Path) -> str:
    return norm_lang(root.get("language", "")) or stem_lang(path.stem) or path.stem


def convert(ts_path: Path, out_path: Path, src_lang: str | None) -> tuple[str, int]:
    root = ET.parse(ts_path).getroot()
    lang = target_lang(root, ts_path)
    src = src_lang or norm_lang(root.get("sourcelanguage", "")) or "en"
    n = write_tmx(out_path, src, lang, ts_path.name, units(root))
    logger.debug(f"{ts_path} -> {out_path} ({lang}, {n} units)")
    return lang, n


def run(
    input: str,
    output: str | None = None,
    src_lang: str | None = None,
    verbose: bool = False,
) -> dict:
    """Convert one .ts file or every .ts under a folder to TMX.

    Args:
        input: a ``.ts`` file or a directory searched recursively.
        output: for a file input, the ``.tmx`` path; for a folder input, an
            output directory mirroring the input tree. Default: next to each ``.ts``.
        src_lang: language of ``<source>`` text (default: ``sourcelanguage``
            attribute, else ``en``).
        verbose: debug logging.
    """
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO")
    src = Path(input).expanduser()
    if not src.exists():
        raise SystemExit(f"input not found: {src}")
    jobs = plan_jobs(src, Path(output) if output else None, ".ts")
    if not jobs:
        raise SystemExit(f"no .ts files under {src}")
    lang = str(src_lang) if src_lang is not None else None
    return convert_all(
        TOOL, src, jobs, lambda source, target: convert(source, target, lang)
    )
