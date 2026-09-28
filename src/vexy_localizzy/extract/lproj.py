# this_file: src/vexy_localizzy/extract/lproj.py
"""Extract Apple localization strings from a macOS .app bundle into TMX files.

Sources discovered by walking the bundle:

* Classic ``<lang>.lproj/*.strings`` (text or plist) and ``*.stringsdict``.
* Compiled ``*.loctable`` (binary plist keyed by language, macOS 13+); the
  ``LocProvenance`` key is metadata and is skipped.

Plural and device-specific dictionaries are flattened (``key|var|cat``; device
variants prefer ``mac``). Each ``<lang>.tmx`` pairs the English text of a key
with the target text: ``en.lproj`` is the pivot and ``Base.lproj`` /
``English.lproj`` fill gaps. A ``.strings`` key that is an English sentence
serves as its own source. Keys go to ``tuid``, the table to ``x-domain`` and
the file to ``x-origin``. Ported from fl10n ``tools/lproj2tmx.py``.
"""

import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path

from loguru import logger

from vexy_localizzy.extract.adobe import PIVOT, Entry, rel
from vexy_localizzy.extract.apple_resources import (
    flatten_value,
    loctable_tables,
    resource_items,
)
from vexy_localizzy.extract.apple_resources import (
    parse_strings_text as parse_strings_text,
)
from vexy_localizzy.extract.legacy_lang import clean_text, norm_lang
from vexy_localizzy.memory.tmx_write import TMXRecord, write_records

__all__ = [
    "Entry",
    "build_tables",
    "extract",
    "loctable_tables",
    "parse_loctable",
    "parse_lproj_file",
    "parse_strings_text",
    "pivot_text",
    "run",
    "write_tmx",
]

BASE_LANGS = {"base": "en", "english": "en"}
# Legacy English-named .lproj folders (pre-10.4 style bundles).
LANG_NAMES = {
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "italian": "it",
    "dutch": "nl",
    "japanese": "ja",
    "chinese": "zh-CN",
    "korean": "ko",
    "portuguese": "pt",
    "swedish": "sv",
    "danish": "da",
    "norwegian": "nb",
    "finnish": "fi",
    "polish": "pl",
    "russian": "ru",
}
STRIP_PARTS = {"Contents", "Resources"}
SKIP_DIRS = {"_CodeSignature", "node_modules"}


def lproj_lang(name: str) -> tuple[str | None, bool]:
    """(language, is_fallback) for an ``.lproj`` folder name."""
    stem = name[:-6].lower()
    if stem in BASE_LANGS:
        return BASE_LANGS[stem], True
    if stem in LANG_NAMES:
        return LANG_NAMES[stem], False
    return norm_lang(stem), False


def domain_for(path: Path, root: Path) -> str:
    """Table name shared across languages: bundle-relative path without lproj."""
    parts = [
        p
        for p in path.relative_to(root).parts
        if not p.endswith(".lproj") and p not in STRIP_PARTS
    ]
    name = "/".join(parts)
    return name.removesuffix(".loctable")


def parse_lproj_file(path: Path, root: Path) -> Iterator[tuple[bool, Entry]]:
    lang, fallback = lproj_lang(path.parent.name)
    if lang is None:
        return
    data = path.read_bytes()
    domain, origin = domain_for(path, root), rel(path, root)
    items = resource_items(data)
    for key, value in items:
        for k, text in flatten_value(key, value):
            yield fallback, Entry(domain, k, lang, text, origin)


def parse_loctable(path: Path, root: Path) -> Iterator[tuple[bool, Entry]]:
    items = loctable_tables(path.read_bytes())
    domain, origin = domain_for(path, root), rel(path, root)
    for raw_lang, table in items:
        lang, fallback = lproj_lang(raw_lang + ".lproj")
        if lang is None:
            continue
        for key, value in table.items():
            for k, text in flatten_value(key, value):
                yield fallback, Entry(domain, k, lang, text, origin)


def walk(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if any(p in SKIP_DIRS for p in path.parts) or path.is_symlink():
            continue
        if not path.is_file():
            continue
        if path.suffix == ".loctable":
            yield path
        elif (
            path.suffix in (".strings", ".stringsdict")
            and path.parent.suffix == ".lproj"
        ):
            yield path


def extract(
    root: Path, include_infoplist: bool
) -> tuple[list[tuple[bool, Entry]], Counter]:
    entries: list[tuple[bool, Entry]] = []
    stats: Counter = Counter()
    for path in walk(root):
        if not include_infoplist and path.stem == "InfoPlist":
            continue
        kind = "loctable" if path.suffix == ".loctable" else "lproj"
        try:
            before = len(entries)
            parser = parse_loctable if kind == "loctable" else parse_lproj_file
            entries.extend(parser(path, root))
            stats[kind] += len(entries) - before
            stats[f"files:{kind}"] += 1
        except Exception as exc:  # noqa: BLE001
            stats["errors"] += 1
            logger.error("Failed {}: {}", path, exc)
    return entries, stats


def build_tables(
    entries: list[tuple[bool, Entry]],
) -> dict[str, dict[tuple[str, str], Entry]]:
    tables: dict[str, dict[tuple[str, str], Entry]] = defaultdict(dict)
    # Real language folders first so Base/English only fill gaps in "en".
    for _, e in sorted(entries, key=lambda t: t[0]):
        text = clean_text(e.text).strip()
        key = clean_text(e.key).strip()
        if not text or not key:
            continue
        tables[e.lang].setdefault(
            (e.domain, key), Entry(e.domain, key, e.lang, text, e.origin)
        )
    return tables


def pivot_text(
    domain: str, key: str, pivot: dict[tuple[str, str], Entry]
) -> str | None:
    src = pivot.get((domain, key))
    if src:
        return src.text
    if "|" in key:
        # Plural category missing in English (few/many): pair with "other".
        base, var, _cat = key.rsplit("|", 2)
        src = pivot.get((domain, f"{base}|{var}|other"))
        return src.text if src else None
    return key if " " in key else None


def write_tmx(
    path: Path,
    lang: str,
    table: dict[tuple[str, str], Entry],
    pivot: dict[tuple[str, str], Entry],
    dedupe: bool,
    skip_identical: bool,
) -> tuple[int, int]:
    """Keep resource pairing policy; delegate XML and atomic publication to Localizzy."""
    paired = 0

    def records():
        nonlocal paired
        seen: set[tuple[str, str]] = set()
        for (domain, key), entry in sorted(table.items()):
            source = pivot_text(domain, key, pivot) if lang != PIVOT else None
            if skip_identical and source == entry.text:
                continue
            signature = (source or key, entry.text)
            if dedupe and signature in seen:
                continue
            seen.add(signature)
            segments = (
                ((PIVOT, source), (lang, entry.text))
                if source
                else ((lang, entry.text),)
            )
            paired += bool(source)
            yield TMXRecord(
                key, segments, (("x-domain", domain), ("x-origin", entry.origin))
            )

    written = write_records(
        path,
        records(),
        source_lang=PIVOT,
        creation_tool="lproj2tmx",
        origin_format="AppleResources",
    )
    return written, paired


def run(
    app: str,
    output: str,
    dedupe: bool = True,
    skip_identical: bool = False,
    include_infoplist: bool = False,
    verbose: bool = False,
) -> dict:
    """Convert an .app bundle's .lproj/.strings and .loctable files into per-language TMX.

    Args:
        app: Bundle folder, e.g. "/System/Applications/Font Book.app".
        output: Folder that receives <lang>.tmx files (created if missing).
        dedupe: Collapse identical (source, target) pairs within a language.
        skip_identical: Drop units whose target equals the English source.
        include_infoplist: Also read InfoPlist bundle metadata tables.
        verbose: Debug logging.
    """
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO")
    root = Path(app).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"App folder not found: {root}")
    out = Path(output).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    logger.info("Scanning {}", root)
    entries, stats = extract(root, include_infoplist)
    logger.info("Extracted {} raw entries: {}", len(entries), dict(stats))
    if stats["errors"]:
        raise SystemExit(
            "Extraction has resource errors; existing outputs were preserved"
        )
    tables = build_tables(entries)
    pivot = tables.get(PIVOT, {})
    languages = []
    for tmx_lang in sorted(tables):
        target = out / f"{tmx_lang}.tmx"
        written, paired = write_tmx(
            target, tmx_lang, tables[tmx_lang], pivot, dedupe, skip_identical
        )
        languages.append(
            {
                "language": tmx_lang,
                "units": written,
                "paired": paired,
                "file": str(target),
            }
        )
    if not tables:
        logger.warning("No localization strings found under {}", root)
    return {
        "tool": "lproj2tmx",
        "app": str(root),
        "languages": languages,
        "stats": dict(stats),
    }
