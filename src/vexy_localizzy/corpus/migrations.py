# this_file: src/vexy_localizzy/corpus/migrations.py
"""Transactional migration of the initial corpus schema; no source files change."""

import sqlite3

from vexy_localizzy.corpus.schema import SCHEMA
from vexy_localizzy.corpus.source_policy import SourcePolicy

TABLES = ("families", "sources", "entries", "candidates", "occurrences", "exclusions")


def migrate_v1(db: sqlite3.Connection) -> None:
    """Preserve IDs and observations while adding independent origin lineage."""
    columns = {row[1] for row in db.execute("PRAGMA table_info(sources)")}
    if not {"snapshot", "error_ordinal"} <= columns:
        raise ValueError(
            "Legacy corpus lacks verified source snapshots; retain this database and reimport original inputs into a new corpus"
        )
    db.execute("PRAGMA foreign_keys=OFF")
    rename = "\n".join(f"ALTER TABLE {name} RENAME TO v1_{name};" for name in TABLES)
    try:
        db.executescript(
            "BEGIN IMMEDIATE; DROP VIEW scores; DROP INDEX occurrence_candidate;\n"
            + rename
            + "\n"
            + SCHEMA
        )
        db.execute("INSERT INTO families SELECT * FROM v1_families")
        for source in db.execute(
            "SELECT s.*,f.name,f.weight FROM v1_sources s JOIN v1_families f ON f.id=s.family_id"
        ).fetchall():
            policy = SourcePolicy(source["name"], source["weight"]).identity
            db.execute(
                "INSERT INTO sources(id,path,sha256,snapshot,family_id,policy,status,active,progress,error,error_ordinal) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    source["id"],
                    source["path"],
                    source["sha256"],
                    source["snapshot"],
                    source["family_id"],
                    policy,
                    source["status"],
                    source["active"],
                    source["progress"],
                    source["error"],
                    source["error_ordinal"],
                ),
            )
        db.execute("INSERT INTO entries(id,source) SELECT id,source FROM v1_entries")
        db.execute(
            "INSERT INTO candidates(id,entry_id,locale,target) SELECT * FROM v1_candidates"
        )
        db.execute("INSERT INTO occurrences SELECT * FROM v1_occurrences")
        db.execute("INSERT INTO exclusions SELECT * FROM v1_exclusions")
        db.execute(
            "INSERT INTO origins(id,path,sha256,snapshot) SELECT id,path,sha256,snapshot FROM v1_sources"
        )
        db.execute(
            "INSERT INTO lineage SELECT o.source_id,o.ordinal,o.candidate_id,o.source_id,o.ordinal,s.family_id FROM v1_occurrences o JOIN v1_sources s ON s.id=o.source_id"
        )
        for name in reversed(TABLES):
            db.execute(f"DROP TABLE v1_{name}")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Corpus migration produced invalid foreign keys")
        db.execute("PRAGMA user_version=2")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.execute("PRAGMA foreign_keys=ON")
