# this_file: src/vexy_localizzy/lineage_validation.py
"""Bounded raw-occurrence verification of imported compact provenance."""

import hashlib
import json
import sqlite3
import tempfile
import unicodedata
from pathlib import Path

from vexy_localizzy.memory.tmx_read import read_tmx


def fingerprint(source, target) -> bytes:
    values = [
        source.text,
        source.xml if source.inline else "",
        target.language,
        target.text,
        target.xml if target.inline else "",
    ]
    values = [
        unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
        for value in values
    ]
    return hashlib.sha256(json.dumps(values, ensure_ascii=False).encode()).digest()


def verify_lineage(path: Path, lineage) -> None:
    """Check every requested original TU/text pair with one scan per original file."""
    with tempfile.TemporaryDirectory(prefix="localizzy-lineage-") as directory:
        with sqlite3.connect(Path(directory) / "requests.sqlite") as db:
            db.execute(
                "CREATE TABLE requests(origin INTEGER, ordinal INTEGER, key BLOB, found INTEGER DEFAULT 0, PRIMARY KEY(origin,ordinal,key)) WITHOUT ROWID"
            )
            for unit in read_tmx(path):
                refs = lineage.references(unit)
                source = unit.english()
                targets = [
                    s
                    for s in unit.segments
                    if not s.language.startswith("en-") and s.language != "en"
                ]
                if source is None or len(targets) != 1:
                    raise ValueError("Invalid lineage source/target variants")
                key = fingerprint(source, targets[0])
                db.executemany(
                    "INSERT OR IGNORE INTO requests(origin,ordinal,key) VALUES (?,?,?)",
                    [(origin, ordinal, key) for origin, ordinal, _ in refs],
                )
            db.commit()
            for (origin,) in db.execute("SELECT DISTINCT origin FROM requests"):
                for unit in read_tmx(lineage.snapshots[origin]):
                    wanted = db.execute(
                        "SELECT key FROM requests WHERE origin=? AND ordinal=?",
                        (origin, unit.ordinal),
                    ).fetchall()
                    if not wanted:
                        continue
                    source = unit.english()
                    if source is None:
                        continue
                    keys = {
                        fingerprint(source, target)
                        for target in unit.segments
                        if target.language.split("-")[0] != "en"
                    }
                    db.executemany(
                        "UPDATE requests SET found=1 WHERE origin=? AND ordinal=? AND key=?",
                        [
                            (origin, unit.ordinal, row[0])
                            for row in wanted
                            if row[0] in keys
                        ],
                    )
                db.commit()
            if db.execute("SELECT 1 FROM requests WHERE found=0 LIMIT 1").fetchone():
                raise ValueError(
                    "Invalid lineage: original ordinal or source/target content does not match"
                )
