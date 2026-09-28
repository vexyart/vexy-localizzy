# this_file: src/vexy_localizzy/export_selection.py
"""Disk-backed source-ID selection and weighted winner staging for TMX exports."""

import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path

WINNERS = """
WITH evidence AS (
 SELECT DISTINCT c.id AS candidate_id,l.family_id,f.weight
 FROM export_selection.entries x
 CROSS JOIN main.candidates c ON c.entry_id=x.id
 CROSS JOIN main.lineage l ON l.candidate_id=c.id
 JOIN main.sources s ON s.id=l.source_id
 JOIN main.families f ON f.id=l.family_id
 WHERE s.active=1 AND s.status='complete'
), scores AS (
 SELECT candidate_id,SUM(weight) AS score,MAX(weight) AS max_weight
 FROM evidence GROUP BY candidate_id
), ranked AS (
 SELECT c.id AS candidate_id,c.entry_id,s.score,s.max_weight,
 ROW_NUMBER() OVER (PARTITION BY c.entry_id,c.locale ORDER BY s.score DESC,s.max_weight DESC,c.target,c.target_xml) AS rank,
 COUNT(*) OVER (PARTITION BY c.entry_id,c.locale,s.score)>1 AS tied
 FROM scores s JOIN main.candidates c ON c.id=s.candidate_id
)
SELECT candidate_id,entry_id,score,max_weight,tied FROM ranked WHERE rank=1
"""


@contextmanager
def staging(db, parent):
    """Use an explicit disk file without changing caller TEMP-table settings."""
    attached = False
    with tempfile.NamedTemporaryFile(
        dir=parent, prefix=".localizzy-export-", delete=False
    ) as file:
        path = Path(file.name)
    try:
        db.execute("ATTACH DATABASE ? AS export_selection", (str(path),))
        attached = True
        yield
    finally:
        if attached:
            db.execute("DETACH DATABASE export_selection")
        path.unlink(missing_ok=True)


def source_snapshot(db):
    rows = db.execute(
        "SELECT path,sha256,policy FROM main.sources WHERE active=1 AND status='complete' ORDER BY path"
    )
    return hashlib.sha256(
        json.dumps([list(row) for row in rows], ensure_ascii=False).encode()
    ).hexdigest()


def prepare(db, entry_ids):
    """Resolve every requested source to active winners inside the caller's snapshot."""
    db.execute("CREATE TABLE export_selection.entries(id INTEGER PRIMARY KEY)")
    for key in entry_ids:
        if type(key) is not int or not 0 < key < 2**63:
            raise ValueError("Selected source IDs must be positive SQLite integers")
        try:
            db.execute("INSERT INTO export_selection.entries VALUES (?)", (key,))
        except sqlite3.IntegrityError as error:
            raise ValueError(f"Duplicate selected source ID {key}") from error
    db.execute(
        "CREATE TABLE export_selection.winners(candidate_id INTEGER PRIMARY KEY,entry_id INTEGER,score INTEGER,max_weight INTEGER,tied INTEGER)"
    )
    db.execute("INSERT INTO export_selection.winners " + WINNERS)
    db.execute("CREATE INDEX export_selection.winner_entries ON winners(entry_id)")
    missing = db.execute(
        "SELECT id FROM export_selection.entries x WHERE NOT EXISTS(SELECT 1 FROM export_selection.winners w WHERE w.entry_id=x.id) LIMIT 1"
    ).fetchone()
    if missing:
        raise ValueError(f"Selected source {missing[0]} has no active winner")
    digest, count = hashlib.sha256(), 0
    for (key,) in db.execute("SELECT id FROM export_selection.entries ORDER BY id"):
        digest.update(f"{key}\n".encode())
        count += 1
    return {"version": 1, "entries": count, "entry_ids_sha256": digest.hexdigest()}


def iter_winners(db):
    with closing(
        db.execute("""
        SELECT w.candidate_id,w.entry_id,e.source,e.source_xml,c.locale,c.target,c.target_xml,w.score,w.max_weight,w.tied
        FROM export_selection.winners w JOIN main.candidates c ON c.id=w.candidate_id
        JOIN main.entries e ON e.id=w.entry_id
        ORDER BY e.source,e.source_xml,c.locale,c.id
    """)
    ) as cursor:
        for row in cursor:
            yield dict(row)
