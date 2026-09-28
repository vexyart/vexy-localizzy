# this_file: src/vexy_localizzy/formats/tmx.py
"""Editable TMX language-pair projections backed by the complete original document."""

from pathlib import Path

from vexy_localizzy.catalog import Catalog, Unit, detect_placeholders
from vexy_localizzy.formats.document import SourceDocument
from vexy_localizzy.formats.tmx_tree import (
    languages,
    metadata_projections,
    parse,
    projection_key,
    selected,
    variants,
)
from vexy_localizzy.formats.tmx_write import dump, representative
from vexy_localizzy.formats.xliff_xml import content

__all__ = ["load", "dump"]


def project(raw: bytes, *, source_lang=None, target_lang=None) -> Catalog:
    tree, ns = parse(raw)
    source_lang, target_lang = languages(tree, ns, source_lang, target_lang)
    units, seen = [], set()
    for ordinal, tu in enumerate(tree.getroot().find(ns + "body").findall(ns + "tu")):
        values = variants(tu, ns)
        source = content(selected(values, source_lang, required=True).find(ns + "seg"))
        target_node = selected(values, target_lang)
        target = (
            content(target_node.find(ns + "seg")) if target_node is not None else None
        )
        fields = metadata_projections(tu, ns).get(
            projection_key(source_lang, target_lang), {}
        )
        if not isinstance(fields, dict) or set(fields) & {
            "source",
            "source_hash",
            "record_id",
        }:
            raise ValueError("Invalid Localizzy TMX metadata fields")
        key = fields.get("key", tu.get("tuid") or f"tmx:{ordinal}")
        while key in seen:
            key += f"~tmx:{ordinal}"
        seen.add(key)
        unit = Unit(
            **{
                "context": "",
                "source": source,
                "target": target,
                "state": "translated" if target is not None else "untranslated",
                "notes": ["".join(node.itertext()) for node in tu.findall(ns + "note")],
                "placeholders": detect_placeholders(source),
                **fields,
                "key": key,
                "record_id": f"tmx:{ordinal}",
            }
        )
        if fields and representative(unit) != target:
            raise ValueError("TMX segment differs from retained catalog metadata")
        units.append(unit)
    return Catalog(
        source_lang=source_lang,
        target_lang=target_lang,
        units=units,
        origin_format="tmx",
        document=SourceDocument.capture(raw, "tmx"),
    )


def load(path: str | Path, *, source_lang=None, target_lang=None) -> Catalog:
    """Infer only unambiguous locales; multilingual originals remain fully retained."""
    return project(
        Path(path).read_bytes(), source_lang=source_lang, target_lang=target_lang
    )
