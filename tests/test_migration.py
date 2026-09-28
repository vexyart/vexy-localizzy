# this_file: tests/test_migration.py
"""Schema evolution must preserve existing candidates, votes and raw snapshots."""

import sqlite3
from pathlib import Path

import pytest

from vexy_localizzy.corpus.schema import APPLICATION_ID
from vexy_localizzy.corpus.store import Corpus


def test_legacy_schema_without_snapshots_then_rejects_without_modifying(tmp_path):
    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript((Path(__file__).parent / "fixtures/schema-v1.sql").read_text())
        db.execute("ALTER TABLE sources DROP COLUMN snapshot")
        db.execute("ALTER TABLE sources DROP COLUMN error_ordinal")
        db.execute(f"PRAGMA application_id={APPLICATION_ID}")
        db.execute("PRAGMA user_version=1")
    with pytest.raises(ValueError, match="reimport.*new corpus"):
        Corpus(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1


def test_schema_one_when_opened_then_preserves_votes_and_origin_links(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript((Path(__file__).parent / "fixtures/schema-v1.sql").read_text())
        db.execute(f"PRAGMA application_id={APPLICATION_ID}")
        db.execute("PRAGMA user_version=1")
        db.execute("INSERT INTO families VALUES (1,'alpha',4)")
        db.execute(
            "INSERT INTO sources(id,path,sha256,snapshot,family_id,status,active,progress) VALUES (1,'a.tmx','hash','archive.gz',1,'complete',1,1)"
        )
        db.execute("INSERT INTO entries VALUES (1,'Moon')")
        db.execute("INSERT INTO candidates VALUES (1,1,'pl','Księżyc')")
        db.execute("INSERT INTO occurrences VALUES (1,1,1)")
    with Corpus(path) as corpus:
        assert corpus.db.execute("PRAGMA user_version").fetchone()[0] == 2
        winner = corpus.winners()[0]
        assert winner["score"] == 4 and winner["target"] == "Księżyc"
        assert corpus.provenance(1)[0]["sha256"] == "hash"
        assert not corpus.db.execute("PRAGMA foreign_key_check").fetchall()
