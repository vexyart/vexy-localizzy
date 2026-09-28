# this_file: src/vexy_localizzy/importer.py
"""Bounded resumable imports; only complete stable snapshots contribute votes."""

import os
import sqlite3
from pathlib import Path

from vexy_localizzy.export_lineage import ExportLineage, read_manifest
from vexy_localizzy.inventory import _identity
from vexy_localizzy.lineage_validation import verify_lineage
from vexy_localizzy.snapshots import snapshot
from vexy_localizzy.source_policy import SourcePolicy
from vexy_localizzy.source_store import prepare
from vexy_localizzy.tmx import read_tmx
from vexy_localizzy.unit_writer import UnitWriter


def _report(db: sqlite3.Connection, source_id: int, cached: bool) -> dict:
    total = db.execute(
        "SELECT progress FROM sources WHERE id=?", (source_id,)
    ).fetchone()[0]
    excluded = db.execute(
        "SELECT COUNT(*) FROM exclusions WHERE source_id=?", (source_id,)
    ).fetchone()[0]
    return dict(source_id=source_id, units=total, excluded=excluded, cached=cached)


def _activate(db: sqlite3.Connection, path: Path, source_id: int) -> None:
    db.execute("UPDATE sources SET active=0 WHERE path=?", (str(path),))
    db.execute("UPDATE sources SET active=1,status='complete' WHERE id=?", (source_id,))


def _failure(
    db: sqlite3.Connection,
    path: Path,
    before,
    source_id: int,
    error: BaseException,
    ordinal: int,
) -> None:
    db.rollback()
    try:
        changed = _identity(before) != _identity(path.stat())
    except OSError:
        changed = True
    with db:
        if changed:
            for table in ("lineage", "occurrences", "exclusions"):
                db.execute(f"DELETE FROM {table} WHERE source_id=?", (source_id,))
            db.execute("UPDATE sources SET progress=0 WHERE id=?", (source_id,))
        detail = "source-changed" if changed else f"{type(error).__name__}: {error}"
        db.execute(
            "UPDATE sources SET status='failed',error=?,error_ordinal=? WHERE id=?",
            (detail, getattr(error, "ordinal", ordinal), source_id),
        )


def import_tmx(
    db: sqlite3.Connection,
    path: Path,
    policy: SourcePolicy,
    batch_size: int,
    snapshot_directory: Path,
) -> dict:
    """Read a stable compressed snapshot and checkpoint its completed TU ordinals."""
    path = Path(os.path.abspath(path))
    before = path.stat()
    digest, archived = snapshot(path, snapshot_directory)
    manifest = read_manifest(archived)
    lineage = (
        ExportLineage(db, manifest, snapshot_directory)
        if manifest is not None
        else None
    )
    if lineage is not None:
        verify_lineage(archived, lineage)
        policy = SourcePolicy("vexy-localizzy:derived", 1)
    source, origin = prepare(db, path, digest, archived, policy)
    source_id, progress = source["id"], source["progress"]
    if source["status"] == "complete":
        if _identity(before) != _identity(path.stat()):
            raise ValueError("Source changed during import")
        with db:
            _activate(db, path, source_id)
        return _report(db, source_id, True)
    with db:
        db.execute(
            "UPDATE sources SET status='importing',error=NULL,error_ordinal=NULL WHERE id=?",
            (source_id,),
        )
    writer = UnitWriter(db, source_id, origin, policy, lineage)
    ordinal = progress + 1
    try:
        for unit in read_tmx(archived):
            ordinal = unit.ordinal
            if ordinal <= progress:
                continue
            writer.write(unit)
            db.execute("UPDATE sources SET progress=? WHERE id=?", (ordinal, source_id))
            if ordinal % batch_size == 0:
                db.commit()
            ordinal += 1
        if _identity(before) != _identity(path.stat()):
            raise ValueError("Source changed during import")
        _activate(db, path, source_id)
        db.commit()
    except BaseException as error:
        _failure(db, path, before, source_id, error, ordinal)
        raise
    return _report(db, source_id, False)
