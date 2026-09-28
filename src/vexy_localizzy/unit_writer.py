# this_file: src/vexy_localizzy/unit_writer.py
"""Insert immutable candidates and compact lineage with bounded ID caches."""

import sqlite3
import unicodedata
from functools import lru_cache

from vexy_localizzy.export_lineage import ExportLineage
from vexy_localizzy.exporter import LINEAGE_PROP
from vexy_localizzy.source_policy import SourcePolicy
from vexy_localizzy.source_store import family_id
from vexy_localizzy.tmx import Unit


def normalized(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


class UnitWriter:
    """One import's bounded ID caches and source-family policy."""

    def __init__(
        self,
        db: sqlite3.Connection,
        source_id: int,
        origin_id: int,
        policy: SourcePolicy,
        lineage: ExportLineage | None = None,
    ) -> None:
        self.db, self.source_id, self.origin_id, self.policy = (
            db,
            source_id,
            origin_id,
            policy,
        )
        self.entry = lru_cache(maxsize=8192)(self._entry)
        self.lineage = lineage
        self.candidate = lru_cache(maxsize=8192)(self._candidate)
        self.family = lru_cache(maxsize=1024)(
            lambda name: family_id(db, name, policy.weight)
        )

    def _entry(self, source: str, xml: str) -> int:
        self.db.execute(
            "INSERT OR IGNORE INTO entries(source,source_xml) VALUES (?,?)",
            (source, xml),
        )
        return self.db.execute(
            "SELECT id FROM entries WHERE source=? AND source_xml=?", (source, xml)
        ).fetchone()[0]

    def _candidate(self, entry_id: int, locale: str, target: str, xml: str) -> int:
        key = entry_id, locale, target, xml
        self.db.execute(
            "INSERT OR IGNORE INTO candidates(entry_id,locale,target,target_xml) VALUES (?,?,?,?)",
            key,
        )
        return self.db.execute(
            "SELECT id FROM candidates WHERE entry_id=? AND locale=? AND target=? AND target_xml=?",
            key,
        ).fetchone()[0]

    def exclude(self, unit: Unit, reason: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO exclusions VALUES (?,?,?)",
            (self.source_id, unit.ordinal, reason),
        )

    def write(self, unit: Unit) -> None:
        if self.lineage is None and any(
            name == LINEAGE_PROP for name, _ in unit.properties
        ):
            raise ValueError("Unit lineage requires an export manifest")
        refs = self.lineage.references(unit) if self.lineage is not None else None
        source = unit.english()
        if source is None or not source.text.strip():
            self.exclude(unit, "missing-or-empty-english")
            return
        targets = [
            s
            for s in unit.segments
            if s.language.split("-")[0] != "en" and s.text.strip()
        ]
        if not targets:
            self.exclude(unit, "no-translated-target")
            return
        entry = self.entry(normalized(source.text), source.xml if source.inline else "")
        if refs is None:
            refs = [
                (
                    self.origin_id,
                    unit.ordinal,
                    self.family(self.policy.family_for(unit)),
                )
            ]
        for target in targets:
            candidate = self.candidate(
                entry,
                target.language,
                normalized(target.text),
                target.xml if target.inline else "",
            )
            occurrence = self.source_id, unit.ordinal, candidate
            self.db.execute(
                "INSERT OR IGNORE INTO occurrences VALUES (?,?,?)", occurrence
            )
            self.db.executemany(
                "INSERT OR IGNORE INTO lineage VALUES (?,?,?,?,?,?)",
                [(*occurrence, *ref) for ref in refs],
            )
