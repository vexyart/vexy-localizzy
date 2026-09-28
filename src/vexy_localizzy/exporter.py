# this_file: src/vexy_localizzy/exporter.py
"""Streaming atomic TMX exports with a compact shared origin registry."""

import json
import os
import tempfile
from contextlib import closing, nullcontext
from pathlib import Path

from lxml import etree

from vexy_localizzy import export_selection
from vexy_localizzy.corpus_identity import entry_map_sha256 as entry_map_digest
from vexy_localizzy.tmx import XML_LANG

MANIFEST_PROP = "x-vexy-localizzy-origins"
LINEAGE_PROP = "x-vexy-localizzy-lineage"
DECISION_PROP = "x-vexy-localizzy-decision"


def manifest(db, *, selected=False) -> dict:
    """Only active observations are eligible for export lineage."""
    selection = (
        " JOIN export_selection.winners w ON w.candidate_id=l.candidate_id "
        if selected
        else " "
    )
    origins = db.execute(
        "SELECT DISTINCT r.* FROM origins r JOIN lineage l ON l.origin_id=r.id JOIN sources s ON s.id=l.source_id"
        + selection
        + "WHERE s.active=1 AND s.status='complete' ORDER BY r.id"
    )
    families = db.execute(
        "SELECT DISTINCT f.* FROM families f JOIN lineage l ON l.family_id=f.id JOIN sources s ON s.id=l.source_id"
        + selection
        + "WHERE s.active=1 AND s.status='complete' ORDER BY f.id"
    )
    return {
        "version": 1,
        "origins": {str(r["id"]): dict(r) for r in origins},
        "families": {str(r["id"]): dict(r) for r in families},
    }


def make_unit(corpus, row: dict) -> etree._Element:
    unit = etree.Element("tu", tuid=str(row["candidate_id"]))
    refs = corpus.db.execute(
        "SELECT DISTINCT l.origin_id,l.origin_ordinal,l.family_id FROM lineage l JOIN sources s ON s.id=l.source_id WHERE l.candidate_id=? AND s.active=1 AND s.status='complete' ORDER BY l.origin_id,l.origin_ordinal,l.family_id",
        (row["candidate_id"],),
    )
    etree.SubElement(unit, "prop", type=LINEAGE_PROP).text = json.dumps(
        [list(r) for r in refs], separators=(",", ":")
    )
    etree.SubElement(unit, "prop", type=DECISION_PROP).text = json.dumps(
        {key: row[key] for key in ("score", "max_weight", "tied")},
        separators=(",", ":"),
    )
    for locale, text, xml in (
        ("en", row["source"], row["source_xml"]),
        (row["locale"], row["target"], row["target_xml"]),
    ):
        variant = etree.SubElement(unit, "tuv", {XML_LANG: locale})
        if xml:
            variant.append(
                etree.fromstring(
                    xml.encode(),
                    etree.XMLParser(resolve_entities=False, no_network=True),
                )
            )
        else:
            etree.SubElement(variant, "seg").text = text
    return unit


def check_destination(corpus, path: str | Path) -> None:
    """Protect the live corpus and its managed snapshots from output replacement."""
    path = Path(path)
    destination = path.resolve()
    protected = {
        corpus.path,
        Path(str(corpus.path) + "-wal"),
        Path(str(corpus.path) + "-shm"),
        Path(str(corpus.path) + "-journal"),
    }
    if destination in protected or destination.is_relative_to(
        corpus.path.with_suffix(".sources")
    ):
        raise ValueError(
            "Export destination overlaps the corpus database or source snapshots"
        )


def export_tmx(
    corpus,
    path: str | Path,
    *,
    entry_ids=None,
    source_snapshot=None,
    entry_map_sha256=None,
) -> int:
    """Publish source-selected or complete winners with compact original lineage."""
    path = Path(path).absolute()
    check_destination(corpus, path)
    if corpus.db.in_transaction:
        raise ValueError("Finish the current transaction before exporting")
    if (
        entry_ids is not None
        and source_snapshot is not None
        and entry_map_sha256 is None
    ):
        raise ValueError("A frozen source selection also requires its entry map digest")
    context = (
        export_selection.staging(corpus.db, path.parent)
        if entry_ids is not None
        else nullcontext()
    )
    with context:
        return _export_tmx(
            corpus,
            path,
            entry_ids=entry_ids,
            source_snapshot=source_snapshot,
            entry_map_sha256=entry_map_sha256,
        )


def _export_tmx(
    corpus,
    path: str | Path,
    *,
    entry_ids=None,
    source_snapshot=None,
    entry_map_sha256=None,
) -> int:
    """Publish all winners in one consistent read transaction; retain old file on error."""
    path = Path(path).absolute()
    check_destination(corpus, path)
    temporary = None
    count = 0
    if corpus.db.in_transaction:
        raise ValueError("Finish the current transaction before exporting")
    corpus.db.execute("BEGIN")
    try:
        snapshot = export_selection.source_snapshot(corpus.db)
        if source_snapshot is not None and source_snapshot != snapshot:
            raise ValueError("Corpus source snapshot changed")
        mapping = (
            entry_map_digest(corpus.db)
            if entry_ids is not None or entry_map_sha256 is not None
            else None
        )
        if entry_map_sha256 is not None and mapping != entry_map_sha256:
            raise ValueError("Corpus entry map changed")
        selection = (
            export_selection.prepare(corpus.db, entry_ids)
            if entry_ids is not None
            else None
        )
        header = etree.Element(
            "header",
            creationtool="vexy-localizzy",
            creationtoolversion="1",
            segtype="sentence",
            adminlang="en",
            srclang="en",
            datatype="PlainText",
            **{"o-tmf": "vexy-localizzy"},
        )
        etree.SubElement(header, "prop", type=MANIFEST_PROP).text = json.dumps(
            manifest(corpus.db, selected=selection is not None),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        if selection is not None:
            etree.SubElement(
                header, "prop", type="x-vexy-localizzy-selection"
            ).text = json.dumps(
                {**selection, "source_snapshot": snapshot, "entry_map_sha256": mapping},
                separators=(",", ":"),
            )
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            with etree.xmlfile(output, encoding="utf-8") as writer:
                writer.write_declaration()
                with writer.element("tmx", version="1.4"):
                    writer.write(header)
                    with writer.element("body"):
                        rows = (
                            export_selection.iter_winners(corpus.db)
                            if selection is not None
                            else corpus.iter_winners()
                        )
                        with closing(rows):
                            for row in rows:
                                unit = make_unit(corpus, row)
                                if selection is not None:
                                    identity = etree.Element(
                                        "prop", type="x-vexy-localizzy-source-id"
                                    )
                                    identity.text = str(row["entry_id"])
                                    unit.insert(2, identity)
                                writer.write(unit)
                                count += 1
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        return count
    finally:
        corpus.db.rollback()
        if temporary is not None:
            temporary.unlink(missing_ok=True)
