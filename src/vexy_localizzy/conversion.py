# this_file: src/vexy_localizzy/conversion.py
"""Prepare, inspect and atomically publish catalog conversions."""

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from vexy_localizzy.catalog import Catalog, Finding
from vexy_localizzy.formats import android, i18next, json_io, po, tmx, ts, xliff
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.formats.po_records import parse as parse_po

ADAPTERS = {
    "ts": ts,
    "json": json_io,
    "po": po,
    "xliff": xliff,
    "android": android,
    "i18next": i18next,
    "tmx": tmx,
}


@dataclass(frozen=True)
class ConversionResult:
    catalog: Catalog
    out_path: Path
    findings: list[Finding]


class ConversionLoss(ValueError):
    """The prepared output loses catalog information and has not been approved."""

    def __init__(self, findings: list[Finding]):
        self.findings = findings
        fields = sorted({finding.data["field"] for finding in findings})
        super().__init__(
            f"Conversion changes or drops fields: {', '.join(fields)}. Inspect findings or pass allow_loss=True."
        )


def load_any(
    path: str | Path,
    *,
    source_format: str | None = None,
    source_lang=None,
    target_lang=None,
) -> Catalog:
    path = Path(path)
    format = "po" if path.suffix.lower() == ".pot" else path.suffix.lower().lstrip(".")
    if format == "xlf":
        format = "xliff"
    if format == "xml":
        format = "android"
    if source_format is not None:
        format = source_format
    if format not in ADAPTERS:
        raise ValueError(f"Unsupported input format: {path.suffix}")
    if format == "tmx":
        return tmx.load(path, source_lang=source_lang, target_lang=target_lang)
    if source_lang is not None or target_lang is not None:
        raise ValueError("Language projection options apply only to TMX input")
    return ADAPTERS[format].load(path)


def _prepare(catalog: Catalog, target: str, plural_order: list[str] | None) -> Catalog:
    if target == "json":
        return catalog
    units = []
    android_keys = set()
    for unit in catalog.units:
        updates = {}
        if target == "android" and (
            catalog.document is None or catalog.document.format != "android"
        ):
            key = unit.key
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*(?:\[[0-9]+\])?", key) is None:
                key = re.sub(r"[^A-Za-z0-9_.]", "_", key)
                if not key or not re.match(r"[A-Za-z_]", key):
                    key = "message_" + key
            while key in android_keys:
                key += "_"
            android_keys.add(key)
            updates["key"] = key
        plural = unit.plural
        if (
            target == "ts"
            and plural is not None
            and plural.icu is not None
            and (plural.icu == unit.target or plural.icu == unit.source)
        ):
            # ICU message syntax is a literal string to Qt, not Qt numerus arms.
            # Keep the complete sentence; the loss report records parsed metadata.
            plural = None
        if target in ("ts", "po") and plural is not None and plural.indexing == "cldr":
            if (
                not plural_order
                or len(set(plural_order)) != len(plural_order)
                or set(plural_order) != set(plural.forms)
            ):
                raise ValueError(
                    "Supply plural_order with every source category exactly once"
                )
            plural = plural.model_copy(
                update={
                    "indexing": "index",
                    "forms": {
                        str(i): plural.forms[key] for i, key in enumerate(plural_order)
                    },
                    "variants": {
                        str(i): plural.variants[key]
                        for i, key in enumerate(plural_order)
                        if key in plural.variants
                    },
                }
            )
        if target == "ts" and plural is not None:
            plural = plural.model_copy(update={"icu": None})
        if target == "po":
            if plural is not None:
                updates["source_plural"] = (
                    unit.source_plural
                    if unit.source_plural is not None
                    else unit.source
                )
                plural = plural.model_copy(update={"variants": {}, "icu": None})
            if unit.variants is not None:
                if not unit.variants:
                    raise ValueError("Cannot flatten an empty length-variant list")
                updates.update(target=unit.variants[0], variants=None)
        updates["plural"] = plural
        units.append(unit.model_copy(update=updates))
    document = (
        catalog.document
        if catalog.document is not None and catalog.document.format == target
        else None
    )
    return catalog.model_copy(update={"units": units, "document": document})


def _finding(field: str, key: str | None = None) -> Finding:
    return Finding(
        rule_id="FORMAT-LOSS",
        severity="major",
        message=f"Output changes or omits {field}",
        unit_key=key,
        data={"field": field},
    )


def _losses(before: Catalog, after: Catalog, target: str) -> list[Finding]:
    if len(before.units) != len(after.units):
        raise ValueError("Conversion cannot preserve the complete message set")
    losses = []
    if before.document is not None and target not in ("json", before.document.format):
        losses.append(_finding("document"))
    if before.document is not None and before.document.format == target == "po":
        old_headers = parse_po(before.document.content).metadata
        new_headers = parse_po(after.document.content).metadata
        losses.extend(
            _finding(field)
            for field in sorted(old_headers.keys() | new_headers.keys())
            if old_headers.get(field) != new_headers.get(field)
        )
    for field in ("source_lang", "target_lang"):
        if getattr(before, field) != getattr(after, field):
            losses.append(_finding(field))
    for original, converted in zip(before.units, after.units, strict=True):
        for field, value in original.model_dump(
            exclude={"record_id", "source_hash"}
        ).items():
            if value != converted.model_dump()[field]:
                losses.append(_finding(field, original.key))
    return losses


def convert(
    src: str | Path,
    target: str,
    out: str | Path,
    *,
    allow_loss: bool = False,
    plural_forms: str | None = None,
    plural_order: list[str] | None = None,
    source_format: str | None = None,
    source_lang: str | None = None,
    target_lang: str | None = None,
) -> ConversionResult:
    """Refuse unacknowledged losses; prepare and parse output before replacing OUT."""
    if target not in ADAPTERS:
        raise ValueError(f"Unsupported target format: {target}")
    catalog = load_any(
        src,
        source_format=source_format,
        source_lang=source_lang,
        target_lang=target_lang,
    )
    return convert_catalog(
        catalog,
        target,
        out,
        allow_loss=allow_loss,
        plural_forms=plural_forms,
        plural_order=plural_order,
    )


def convert_catalog(
    catalog: Catalog,
    target: str,
    out: str | Path,
    *,
    allow_loss: bool = False,
    plural_forms: str | None = None,
    plural_order: list[str] | None = None,
) -> ConversionResult:
    """Convert an in-memory catalog using the same loss and atomic-write gates."""
    if target not in ADAPTERS:
        raise ValueError(f"Unsupported target format: {target}")
    prepared = _prepare(catalog, target, plural_order)
    with tempfile.TemporaryDirectory(prefix="localizzy-convert-") as directory:
        temporary = Path(directory) / f"catalog.{target}"
        options = {"plural_forms": plural_forms} if target == "po" else {}
        ADAPTERS[target].dump(prepared, temporary, **options)
        output = ADAPTERS[target].load(
            temporary,
            **(
                {
                    "source_lang": prepared.source_lang,
                    "target_lang": prepared.target_lang,
                }
                if target == "tmx"
                else {}
            ),
        )
        findings = _losses(catalog, output, target)
        if findings and not allow_loss:
            raise ConversionLoss(findings)
        atomic_write(Path(out), temporary.read_bytes())
    return ConversionResult(catalog=catalog, out_path=Path(out), findings=findings)
