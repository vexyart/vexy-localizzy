# this_file: src/vexy_localizzy/extract/po2tmx.py
"""Convert gettext ``.po`` files, or a folder of them, to TMX 1.4.

Source language is the ``msgid`` language (default ``en``). Target language
comes from the ``Language:`` header, else the file stem, else the stem itself.
Untranslated, obsolete and (unless ``fuzzy``) fuzzy entries are skipped. Plural
entries emit ``msgid``/``msgstr[0]`` and ``msgid_plural``/``msgstr[last]``.
``msgctxt`` lands in ``x-context``. Ported from fl10n ``tools/po2tmx.py``.
"""

import sys
from pathlib import Path

import polib
from loguru import logger

from vexy_localizzy.extract.legacy_lang import norm_lang
from vexy_localizzy.extract.legacy_tmx import write_tmx
from vexy_localizzy.extract.walk import convert_all, plan_jobs
from vexy_localizzy.legacy_pairs import po_pairs as units

TOOL = "po2tmx"
__all__ = ["TOOL", "convert", "run", "target_lang", "units", "write_tmx"]


def target_lang(po: polib.POFile, path: Path) -> str:
    header = po.metadata.get("Language", "")
    return norm_lang(header) or norm_lang(path.stem) or path.stem


def convert(
    po_path: Path, out_path: Path, src_lang: str, fuzzy: bool
) -> tuple[str, int]:
    po = polib.pofile(str(po_path), encoding="utf-8")
    lang = target_lang(po, po_path)
    n = write_tmx(out_path, src_lang, lang, po_path.name, units(po, fuzzy))
    logger.debug(f"{po_path} -> {out_path} ({lang}, {n} units)")
    return lang, n


def run(
    input: str,
    output: str | None = None,
    src_lang: str = "en",
    fuzzy: bool = False,
    verbose: bool = False,
) -> dict:
    """Convert one .po file or every .po under a folder to TMX.

    Args:
        input: a ``.po`` file or a directory searched recursively.
        output: for a file input, the ``.tmx`` path; for a folder input, an
            output directory mirroring the input tree. Default: next to each ``.po``.
        src_lang: language of ``msgid`` text (default ``en``).
        fuzzy: include entries flagged fuzzy.
        verbose: debug logging.
    """
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO")
    src = Path(input).expanduser()
    if not src.exists():
        raise SystemExit(f"input not found: {src}")
    jobs = plan_jobs(src, Path(output) if output else None, ".po")
    if not jobs:
        raise SystemExit(f"no .po files under {src}")
    lang = str(src_lang)
    return convert_all(
        TOOL, src, jobs, lambda source, target: convert(source, target, lang, fuzzy)
    )
