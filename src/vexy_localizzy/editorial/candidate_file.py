# this_file: src/vexy_localizzy/editorial/candidate_file.py
"""Read the reviewer's candidates file and keep what the filters and guards accept.

Each JSONL line is one reviewed batch: a ``model`` and its ``corrections``. An id
proposed twice is refused for the whole file, because two proposals for one
message have no safe winner. Kept candidates still face the live-catalog check
in ``apply``; refused ones are listed with the guard's reason.
"""

import json
from collections import Counter
from pathlib import Path

from vexy_localizzy.editorial.guards import problem
from vexy_localizzy.editorial.ledger import Outcome

FAMILIES = (
    "accuracy",
    "terminology",
    "conventions",
    "locale",
    "style",
    "compliance",
    "markup",
    "audience",
)
SEVERITIES = ("critical", "major", "minor")
MARKUP_FAMILY = "markup"
REQUIRED_FIELDS = ("id", "before", "revised")


def _records(path: Path) -> list[dict]:
    """Parsed JSONL records, each with a ``model`` and a ``corrections`` list."""
    records = []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        record = json.loads(line)
        corrections = record.get("corrections") if isinstance(record, dict) else None
        if not isinstance(corrections, list) or not all(
            isinstance(c, dict)
            and all(f in c for f in REQUIRED_FIELDS)
            and isinstance(c["id"], str)
            for c in corrections
        ):
            raise ValueError(f"{path}:{number}: not a review record")
        records.append(record)
    return records


def _refuse_duplicates(records: list[dict], path: Path) -> None:
    """One correction per id: two proposals for one message have no safe winner."""
    counts = Counter(c["id"] for r in records for c in r["corrections"])
    if duplicates := sorted(key for key, n in counts.items() if n > 1):
        raise ValueError(
            f"{path}: {len(duplicates)} ids have more than one candidate "
            f"({', '.join(duplicates[:5])}); remove the extra lines, or review "
            "into a new candidates file"
        )


def load_candidates(
    path: Path,
    severities: set[str],
    families: set[str],
    rejected: set[str],
    *,
    allow_markup: bool = False,
) -> tuple[list[dict], Counter, Outcome]:
    """Kept candidates, counts of the user's filters, and guard refusals by id."""
    records = _records(path)
    _refuse_duplicates(records, path)
    kept, filtered, refused = [], Counter(), Outcome()
    for record in records:
        for c in record["corrections"]:
            if c["id"] in rejected:
                filtered["rejected"] += 1
            elif c.get("severity") not in severities:
                filtered["severity"] += 1
            elif c.get("family") not in families:
                filtered["family"] += 1
            elif reason := problem(
                c["before"],
                c["revised"],
                c.get("source"),
                markup=allow_markup and c.get("family") == MARKUP_FAMILY,
            ):
                refused.skip(c, reason)
            else:
                kept.append(dict(c, model=record.get("model", "")))
    return kept, filtered, refused
