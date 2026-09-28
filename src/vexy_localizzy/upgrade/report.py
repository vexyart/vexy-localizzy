# this_file: src/vexy_localizzy/upgrade/report.py
"""The upgrade report: one outcome per FRESH message plus file identities."""

import hashlib
from typing import Literal

from pydantic import Field

from vexy_localizzy.catalog import Record

Category = Literal[
    "exact",
    "exact_unfinished",
    "shape_changed",
    "plural_count_changed",
    "memory_id",
    "memory_context",
    "relocated",
    "fuzzy_exact_loose",
    "fuzzy_similar",
    "memory_source",
    "memory_term",
    "machine",
    "pending",
    "untranslated",
    "excluded_empty",
    "excluded_vanished",
]
TIER_CATEGORIES: tuple[str, ...] = (
    "exact",
    "exact_unfinished",
    "shape_changed",
    "plural_count_changed",
    "memory_id",
    "memory_context",
    "relocated",
    "fuzzy_exact_loose",
    "fuzzy_similar",
    "memory_source",
    "memory_term",
    "machine",
    "pending",
    "untranslated",
)
EXCLUDED_CATEGORIES: tuple[str, ...] = ("excluded_empty", "excluded_vanished")


class FileInfo(Record):
    path: str | None = None
    sha256: str
    messages: int

    @classmethod
    def of(cls, raw: bytes, messages: int, path: str | None = None) -> "FileInfo":
        return cls(path=path, sha256=hashlib.sha256(raw).hexdigest(), messages=messages)


class MessageOutcome(Record):
    fresh_ordinal: int
    context: str
    source: str
    category: Category
    state: Literal["finished", "unfinished", "untouched"]
    filled: bool  # NEW carries translation text for this message
    approved_ordinal: int | None = None
    approved_source: str | None = None
    similarity: float | None = None
    memory: str | None = None
    tuids: list[str] = Field(default_factory=list)
    glossary_terms: list[str] = Field(default_factory=list)
    model: str | None = None


class UpgradeReport(Record):
    schema_id: Literal["localizzy-upgrade/1"] = "localizzy-upgrade/1"
    fresh: FileInfo
    approved: FileInfo
    out: FileInfo
    retired: FileInfo
    target_lang: str
    memories: list[dict] = Field(default_factory=list)
    options: dict = Field(default_factory=dict)
    counts: dict[str, int]
    messages: list[MessageOutcome]
    retired_ordinals: list[int] = Field(default_factory=list)
    invariants: dict[str, bool]

    @property
    def unfilled(self) -> int:
        """Active FRESH messages whose NEW translation is still empty."""
        return sum(
            1
            for m in self.messages
            if m.category not in EXCLUDED_CATEGORIES and not m.filled
        )

    @property
    def ok(self) -> bool:
        return all(self.invariants.values())


def count_outcomes(
    outcomes: list[MessageOutcome], retired_active: int, retired_obsolete: int
) -> dict[str, int]:
    counts = {name: 0 for name in (*TIER_CATEGORIES, *EXCLUDED_CATEGORIES)}
    for outcome in outcomes:
        counts[outcome.category] += 1
    counts["retired_active"] = retired_active
    counts["retired_obsolete"] = retired_obsolete
    counts["unfilled"] = sum(
        1 for o in outcomes if o.category not in EXCLUDED_CATEGORIES and not o.filled
    )
    return counts


def invariants(
    outcomes: list[MessageOutcome],
    fresh_total: int,
    fresh_active: int,
    approved_total: int,
    consumed: set[int],
    retired: set[int],
) -> dict[str, bool]:
    """Every FRESH message has one outcome; every APPROVED message is used or retired."""
    ordinals = [o.fresh_ordinal for o in outcomes]
    tiered = sum(1 for o in outcomes if o.category in TIER_CATEGORIES)
    return {
        "every_fresh_classified": sorted(ordinals) == list(range(fresh_total))
        and tiered == fresh_active,
        "approved_consumed_or_retired": not (consumed & retired)
        and consumed | retired == set(range(approved_total)),
    }
