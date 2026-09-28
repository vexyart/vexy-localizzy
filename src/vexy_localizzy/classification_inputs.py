# this_file: src/vexy_localizzy/classification_inputs.py
"""Freeze English input and locale coverage from one complete corpus snapshot."""

import hashlib
import json
import os
import tempfile
from contextlib import closing
from pathlib import Path

from vexy_localizzy.corpus.exporter import check_destination
from vexy_localizzy.corpus.identity import entry_map_sha256


def stage_usable(db, *, exporting=False) -> None:
    """Share exact active source/locale eligibility with the completed-run exporter."""
    table = (
        "export_selection.classification_usable"
        if exporting
        else "temp.classification_usable"
    )
    db.execute(
        f"CREATE TABLE {table}(entry_id INTEGER,locale TEXT,PRIMARY KEY(entry_id,locale)) WITHOUT ROWID"
    )
    db.execute(
        f"INSERT OR IGNORE INTO {table} SELECT c.entry_id,c.locale FROM candidates c WHERE EXISTS(SELECT 1 FROM occurrences o JOIN sources s ON s.id=o.source_id WHERE o.candidate_id=c.id AND s.active=1 AND s.status='complete')"
    )


def source_rows(db, *, exporting=False):
    """Stream all usable English IDs, exact text and sorted distinct target locales."""
    table = (
        "export_selection.classification_usable"
        if exporting
        else "temp.classification_usable"
    )
    with closing(
        db.execute(
            f"SELECT e.id,e.source,GROUP_CONCAT(u.locale) FROM entries e JOIN {table} u ON u.entry_id=e.id GROUP BY e.id ORDER BY e.id"
        )
    ) as rows:
        for row in rows:
            yield {"id": row[0], "text": row[1], "locales": sorted(row[2].split(","))}


def prepare_inputs(
    corpus, output: str | Path, *, expected_sources: int | None = None
) -> dict:
    """Atomically write a metadata header and bounded English/locale JSONL records."""
    if corpus.db.in_transaction:
        raise ValueError("Finish the current transaction before preparing input")
    output, temporary = Path(output), None
    check_destination(corpus, output)
    corpus.db.execute("BEGIN")
    try:
        sources = corpus.db.execute(
            "SELECT path,sha256,policy FROM sources WHERE active=1 AND status='complete' ORDER BY path"
        ).fetchall()
        if expected_sources is not None and len(sources) != expected_sources:
            raise ValueError(
                "Active source count does not match the expected source count"
            )
        if corpus.db.execute(
            "SELECT 1 FROM sources WHERE status<>'complete' LIMIT 1"
        ).fetchone():
            raise ValueError("Corpus contains pending or failed source imports")
        stage_usable(corpus.db)
        coverage = dict(
            corpus.db.execute(
                "SELECT locale,COUNT(*) FROM classification_usable GROUP BY locale ORDER BY locale"
            )
        )
        count = corpus.db.execute(
            "SELECT COUNT(DISTINCT entry_id) FROM classification_usable"
        ).fetchone()[0]
        metadata = {
            "type": "metadata",
            "version": 1,
            "entries": count,
            "sources": len(sources),
            "source_snapshot": hashlib.sha256(
                json.dumps([list(row) for row in sources], ensure_ascii=False).encode()
            ).hexdigest(),
            "coverage": coverage,
            "entry_map_sha256": entry_map_sha256(corpus.db),
        }
        with tempfile.NamedTemporaryFile(
            dir=output.parent, mode="w", encoding="utf-8", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(metadata, ensure_ascii=False) + "\n")
            with closing(source_rows(corpus.db)) as rows:
                for row in rows:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
        return metadata
    finally:
        corpus.db.rollback()
        if temporary is not None:
            temporary.unlink(missing_ok=True)
