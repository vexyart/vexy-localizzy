# this_file: src/vexy_localizzy/memory/qph.py
"""Export plain-text TMX pairs using Qt Linguist's phrase book XML format."""

import os
import tempfile
from pathlib import Path

from loguru import logger
from lxml import etree

from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.tmx_read import Segment, Unit, read_tmx


def _segment(unit: Unit, language: str) -> Segment:
    choices = [s for s in unit.segments if s.language == language]
    if len(choices) != 1:
        raise ValueError(f"TU {unit.ordinal}: Expected one {language} segment")
    segment = choices[0]
    if segment.inline:
        raise ValueError(
            f"TU {unit.ordinal}: Inline TMX markup cannot be stored in QPH"
        )
    if not segment.text.strip():
        raise ValueError(f"TU {unit.ordinal}: Empty {language} segment")
    return segment


def _phrase(unit: Unit, source: str, target: str) -> etree._Element:
    original, translated = _segment(unit, source), _segment(unit, target)
    phrase = etree.Element("phrase")
    etree.SubElement(phrase, "source").text = original.text
    etree.SubElement(phrase, "target").text = translated.text
    status = dict(unit.properties).get("x-status")
    notes = [f"Status: {status}"] if status else []
    notes.extend((*unit.notes, *original.notes, *translated.notes))
    if notes:
        etree.SubElement(phrase, "definition").text = "\n\n".join(notes)
    return phrase


def tmx2qph(
    input: str,
    output: str,
    target: str,
    src_lang: str = "en",
    verbose: bool = False,
) -> dict:
    """Convert a TMX file to a Qt phrase book, retaining every pair in input order.

    Args:
        input: source TMX (or .tmx.gz) file.
        output: destination .qph file, atomically replaced after validation.
        target: exact target language tag, for example de or es-419.
        src_lang: exact source language tag (default en).
        verbose: log the input, language pair and output count.

    Notes and x-status become definitions. Proposed and identical translations
    are retained; Qt does not enforce review status. Other TMX properties are
    not exported. Missing, duplicate, empty or inline-marked segments fail
    explicitly, preserving an existing output. No translations are invented.

    Export replaces an existing phrase book; it does not merge manual edits.
    Before rebuilding a curated QPH, export to a scratch path, compare targets
    and definitions, and reconcile approved changes into the source TMX first.
    """
    source_path, output_path = Path(input), Path(output)
    if source_path.resolve() == output_path.resolve():
        raise ValueError("Input and output must be different files")
    source, target = canonical_locale(src_lang), canonical_locale(target)
    root = etree.Element(
        "QPH",
        language=target.replace("-", "_"),
        sourcelanguage=source.replace("-", "_"),
    )
    for unit in read_tmx(source_path):
        root.append(_phrase(unit, source, target))
    if not len(root):
        raise ValueError("No translation units to export")
    data = etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
        doctype="<!DOCTYPE QPH>",
        pretty_print=True,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent, prefix=f".{output_path.name}.", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.replace(temporary, output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if verbose:
        logger.debug(
            "{}: {} → {}, {} phrases → {}",
            source_path,
            source,
            target,
            len(root),
            output_path,
        )
    return {
        "output": str(output_path),
        "source": source,
        "target": target,
        "phrases": len(root),
    }
