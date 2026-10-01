# this_file: src/vexy_localizzy/editorial/ledger.py
"""Ledger records shared by the catalog and JSON appliers: changes, skips, stale.

A correction lands only while the file still holds what the reviewer saw: the
live English source equals the candidate's ``source`` and the live translation
its ``before``. Everything else is recorded here, never applied silently.
"""

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from vexy_localizzy.formats.document import atomic_write

LEDGER_INDENT = 1
ALREADY_APPLIED, UNCHANGED = "already_applied", "unchanged"


def check_live(c: dict, live_source: object, live_target: object) -> str | None:
    """Why candidate ``c`` is stale against the live source and target, or None."""
    if c.get("source") is not None and c["source"] != live_source:
        return "source changed"
    if c["before"] != live_target:
        return "translation changed"
    return None


def settled(c: dict, live_source: object, live_target: object) -> str | None:
    """``already_applied`` when the live text already is the revision (a rerun),
    ``unchanged`` when the revision repeats the reviewed text, else None."""
    if c.get("source") is not None and c["source"] != live_source:
        return None
    if live_target != c["revised"]:
        return None
    return UNCHANGED if c["before"] == c["revised"] else ALREADY_APPLIED


def stale_entry(
    c: dict, reason: str, live_source: object = None, live_target: object = None
) -> dict:
    """A ledger record of a candidate that no longer matches the file."""
    return {
        "id": c["id"],
        "reason": reason,
        "expected_source": c.get("source"),
        "live_source": live_source,
        "expected_before": c["before"],
        "live_target": live_target,
        "revised": c["revised"],
    }


def skip_entry(c: dict, reason: str) -> dict:
    """A ledger record of a candidate left out for ``reason`` (not a user filter)."""
    return {"id": c["id"], "reason": reason, "revised": c["revised"]}


def change_record(
    language: str, key: str, context: str, source: str, before: object, c: dict
) -> dict:
    """A ledger record of one applied correction."""
    return {
        "language": language,
        "id": key,
        "context": context,
        "source": source,
        "before": before,
        "after": c["revised"],
        "why": c.get("reason", ""),
        "family": c.get("family"),
        "severity": c.get("severity"),
        "model": c["model"],
    }


@dataclass
class Outcome:
    """What an applier did: applied changes, stale candidates, listed skips."""

    applied: list[dict] = field(default_factory=list)
    stale: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)

    def skip(self, c: dict, reason: str) -> None:
        self.skipped.append(skip_entry(c, reason))


@dataclass
class Applied:
    """An applier's outcome and, when something changed, how to render the new file."""

    outcome: Outcome
    render: Callable[[Path], None] | None = None


def write_json(path: Path, data: object, *, indent: int = 2) -> None:
    """Write ``data`` as UTF-8 JSON with a trailing newline, atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=indent) + "\n"
    atomic_write(path, text.encode("utf-8"))
