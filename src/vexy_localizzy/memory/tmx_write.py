# this_file: src/vexy_localizzy/memory/tmx_write.py
"""Streaming TMX serialization for newly extracted plain-text resource records.

Use formats.tmx for original-document editing and Corpus.export_tmx for weighted
lineage exports. This writer retains each supplied record/property without
deduplicating, interpreting markup in text, or inventing source provenance.
"""

import os
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.tmx_read import XML_LANG


@dataclass(frozen=True)
class TMXRecord:
    """A key, literal language/text variants and ordered provenance properties."""

    key: str
    segments: tuple[tuple[str, str], ...]
    properties: tuple[tuple[str, str], ...] = ()


def _element(record: TMXRecord) -> etree._Element:
    if not record.segments:
        raise ValueError("A generated TMX record needs at least one language variant")
    unit = etree.Element("tu", tuid=record.key)
    for name, value in record.properties:
        etree.SubElement(unit, "prop", type=name).text = value
    for language, text in record.segments:
        canonical_locale(language)  # Validate but preserve the caller's spelling.
        variant = etree.SubElement(unit, "tuv", {XML_LANG: language})
        etree.SubElement(variant, "seg").text = text
    return unit


def write_records(
    path: str | Path,
    records: Iterable[TMXRecord],
    *,
    source_lang: str,
    creation_tool: str = "vexy-localizzy",
    origin_format: str = "plaintext",
    header_properties: Sequence[tuple[str, str]] = (),
    header_note: str | None = None,
    creation_date: str | None = None,
) -> int:
    """Atomically write a single-pass iterable; extraction errors preserve OUT."""
    canonical_locale(source_lang)
    attributes = {
        "creationtool": creation_tool,
        "creationtoolversion": "1.0",
        "segtype": "block",
        "adminlang": "en",
        "srclang": source_lang,
        "datatype": "plaintext",
        "o-tmf": origin_format,
    }
    if creation_date:
        attributes["creationdate"] = creation_date
    header = etree.Element("header", attributes)
    for name, value in header_properties:
        etree.SubElement(header, "prop", type=name).text = value
    if header_note:
        etree.SubElement(header, "note").text = header_note
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    count = 0
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as output:
            temporary = Path(output.name)
            with etree.xmlfile(output, encoding="utf-8") as writer:
                writer.write_declaration()
                with writer.element("tmx", version="1.4"):
                    writer.write(header)
                    with writer.element("body"):
                        for record in records:
                            writer.write(_element(record))
                            count += 1
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        return count
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
