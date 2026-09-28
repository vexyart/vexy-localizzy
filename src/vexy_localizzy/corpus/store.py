# this_file: src/vexy_localizzy/corpus/store.py
"""Traceable SQLite translation candidates with versioned input snapshots."""

import os
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from vexy_localizzy.corpus.exporter import export_tmx
from vexy_localizzy.corpus.importer import import_tmx
from vexy_localizzy.corpus.migrations import migrate_v1
from vexy_localizzy.corpus.schema import APPLICATION_ID, SCHEMA, SCHEMA_VERSION, WINNERS
from vexy_localizzy.corpus.source_policy import SourcePolicy


class Corpus:
    """A single-writer corpus; completed source snapshots alone contribute votes."""

    def __init__(self, path: str | Path, *, batch_size: int = 1000) -> None:
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.path, self.batch_size = Path(path).resolve(), batch_size
        self.db = sqlite3.connect(self.path, timeout=30)
        self.db.row_factory = sqlite3.Row
        try:
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            tables = self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if version == 0 and not tables:
                self.db.executescript(SCHEMA)
                self.db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                self.db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            elif (
                version == 1
                and self.db.execute("PRAGMA application_id").fetchone()[0]
                == APPLICATION_ID
            ):
                migrate_v1(self.db)
            elif (
                version != SCHEMA_VERSION
                or self.db.execute("PRAGMA application_id").fetchone()[0]
                != APPLICATION_ID
            ):
                raise ValueError("Unknown corpus schema; refusing to adopt database")
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.execute("PRAGMA journal_mode=WAL")
        except Exception:
            self.db.close()
            raise

    def __enter__(self) -> "Corpus":
        return self

    def __exit__(self, *_args) -> None:
        self.db.close()

    def import_tmx(
        self,
        path: str | Path,
        *,
        family: str,
        weight: int,
        family_property: str | None = None,
        family_map: dict[str, str] | None = None,
    ) -> dict:
        """Import or resume a stable source; new versions replace old votes atomically."""
        return import_tmx(
            self.db,
            Path(path),
            SourcePolicy(family, weight, family_property, dict(family_map or {})),
            self.batch_size,
            self.path.with_suffix(".sources"),
        )

    def winners(self) -> list[dict]:
        """Return deterministic winners; alternatives remain in the database."""
        return [dict(row) for row in self.db.execute(WINNERS)]

    def export_tmx(
        self,
        path: str | Path,
        *,
        entry_ids: Iterable[int] | None = None,
        source_snapshot: str | None = None,
        entry_map_sha256: str | None = None,
    ) -> int:
        """Export all or selected source winners, optionally requiring a frozen snapshot."""
        return export_tmx(
            self,
            path,
            entry_ids=entry_ids,
            source_snapshot=source_snapshot,
            entry_map_sha256=entry_map_sha256,
        )

    def iter_winners(self):
        """Stream winners for exports too large to retain in memory."""
        for row in self.db.execute(WINNERS):
            yield dict(row)

    def provenance(self, candidate_id: int) -> list[dict]:
        """Resolve compact occurrence links to active source hashes and ordinals."""
        rows = self.db.execute(
            """
            SELECT DISTINCT r.id AS origin_id,r.path,r.sha256,r.snapshot,o.origin_ordinal AS ordinal,f.name AS family,f.weight
            FROM lineage o JOIN sources s ON s.id=o.source_id
            JOIN families f ON f.id=o.family_id JOIN origins r ON r.id=o.origin_id
            WHERE o.candidate_id=? AND s.active=1 AND s.status='complete'
            ORDER BY r.path,o.origin_ordinal
        """,
            (candidate_id,),
        )
        return [dict(row) for row in rows]

    def deactivate(self, path: str | Path) -> None:
        """Explicitly retract a source path; preserve its occurrences for lineage."""
        with self.db:
            self.db.execute(
                "UPDATE sources SET active=0 WHERE path=?", (os.path.abspath(path),)
            )
