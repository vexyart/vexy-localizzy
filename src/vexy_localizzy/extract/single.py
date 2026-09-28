# this_file: src/vexy_localizzy/extract/single.py
"""Explicit plain-text TMX extraction from bilingual or key-paired resources."""

import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

import polib
from loguru import logger

from vexy_localizzy.extract.legacy_pairs import Pair, po_pairs, ts_pairs
from vexy_localizzy.extract.source_resources import _resource_rows, loctable_rows
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.tmx_write import TMXRecord, write_records

FORMATS = {
    "ts",
    "po",
    "strings",
    "stringsdict",
    "ftl",
    "properties",
    "mozilla-properties",
    "dtd",
    "loctable",
    "json",
}


def _catalog_rows(path: Path, kind: str, fuzzy: bool) -> tuple[list[Pair], str, str]:
    if kind == "po":
        catalog = polib.pofile(str(path))
        return (
            po_pairs(catalog, fuzzy=fuzzy),
            catalog.metadata.get("X-Source-Language", "en"),
            catalog.metadata.get("Language", ""),
        )
    root = ET.parse(path).getroot()
    if root.tag != "TS":
        raise ValueError("Expected a Qt TS document")
    return ts_pairs(root), root.get("sourcelanguage", "en"), root.get("language", "")


def _records(
    rows: list[Pair],
    source_lang: str,
    target_lang: str,
    origin: str,
    source_origin: str | None,
    dedupe: bool,
) -> Iterator[TMXRecord]:
    seen = set()
    number = 0
    for source, target, context, plural in rows:
        signature = (source, target, context)
        if not source or not target or (dedupe and signature in seen):
            continue
        seen.add(signature)
        number += 1
        properties = [("x-origin", origin)]
        if source_origin is not None:
            properties.append(("x-source-origin", source_origin))
        if context:
            properties.append(("x-context", context))
        if plural:
            properties.append(("x-plural", plural))
        yield TMXRecord(
            str(number),
            ((source_lang, source), (target_lang, target)),
            tuple(properties),
        )


def extract(
    input: str,
    output: str,
    source: str | None = None,
    source_lang: str | None = None,
    target_lang: str | None = None,
    source_format: str | None = None,
    fuzzy: bool = False,
    dedupe: bool = True,
    verbose: bool = False,
    source_key: str | None = None,
    target_key: str | None = None,
) -> dict:
    """Extract selected TMX pairs from bilingual, paired or multilingual resources.

    TS/PO uses legacy eligible first/last plural projections. Languages come from
    metadata or explicit arguments, never guessed filenames. Source and target
    resource files join by key; loctables select two internal tables. Return every
    unmatched target key. Invalid text/XML preserves the existing output.
    """
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "WARNING")
    path, destination = Path(input).expanduser(), Path(output).expanduser()
    reference = Path(source).expanduser() if source is not None else None
    for item in [path, *([reference] if reference is not None else [])]:
        if not item.is_file():
            raise ValueError(f"Input file does not exist: {item}")
        if destination.resolve() == item.resolve() or (
            destination.exists() and destination.samefile(item)
        ):
            raise ValueError("Extraction output would overwrite input")
    kind = source_format or path.suffix.lstrip(".").lower()
    if kind not in FORMATS:
        raise ValueError(f"Unsupported extraction format: {kind}")
    if kind != "loctable" and (source_key is not None or target_key is not None):
        raise ValueError("Language table keys apply only to loctable input")
    if fuzzy and kind != "po":
        raise ValueError("Fuzzy selection applies only to PO input")
    if kind == "loctable":
        if reference is not None:
            raise ValueError("Loctable input does not accept a separate source file")
        if not target_lang:
            raise ValueError("Target language is missing; specify target_lang")
        rows, unmatched = loctable_rows(
            path, source_key or source_lang or "en", target_key or target_lang
        )
        reference = path
    elif kind in {"ts", "po"}:
        if reference is not None:
            raise ValueError("Bilingual input does not accept a separate source file")
        rows, metadata_source, metadata_target = _catalog_rows(path, kind, fuzzy)
        source_lang, target_lang = (
            source_lang or metadata_source,
            target_lang or metadata_target,
        )
        unmatched = []
    else:
        if reference is None or not target_lang:
            raise ValueError("Keyed resources require source and target_lang")
        rows, unmatched = _resource_rows(path, reference, kind)
    if not target_lang:
        raise ValueError("Target language is missing; specify target_lang")
    source_lang, target_lang = (
        canonical_locale(source_lang or "en"),
        canonical_locale(target_lang),
    )
    count = write_records(
        destination,
        _records(
            rows,
            source_lang,
            target_lang,
            str(path),
            str(reference) if reference else None,
            dedupe,
        ),
        source_lang=source_lang,
        origin_format=kind,
    )
    logger.debug("Extracted {} pairs from {} to {}", count, path, destination)
    return {
        "output": str(destination),
        "units": count,
        "selected_pairs": len(rows),
        "source_lang": source_lang,
        "target_lang": target_lang,
        "unmatched_keys": unmatched,
    }
