# this_file: src/vexy_localizzy/experimental/classification.py
"""Strict bounded prompts and versioned three-model criticality consensus."""

import json
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    id: int
    text: str
    locales: tuple[str, ...]


def request_text(entries: list[Entry], coverage: dict[str, int]) -> str:
    """Number data within each request, without embedding source text as instructions."""
    if not 1 <= len(entries) <= 100:
        raise ValueError("A classification request requires 1–100 entries")
    return json.dumps(
        {
            "locale_coverage": coverage,
            "entries": [
                {
                    "number": 300 + i,
                    "source": entry.text,
                    "target_locales": entry.locales,
                }
                for i, entry in enumerate(entries)
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def batches(
    entries: Iterable[Entry],
    *,
    max_bytes: int = 64000,
    max_entry_bytes: int | None = None,
) -> Iterator[list[Entry]]:
    """Bound UTF-8 batches; optional larger individual budget permits singletons."""
    max_entry_bytes = max_bytes if max_entry_bytes is None else max_entry_bytes
    if max_bytes < 1 or max_entry_bytes < 1:
        raise ValueError("Positive byte budget required")
    current, size = [], 0
    for entry in entries:
        item_size = len(request_text([entry], {}).encode())
        if item_size > max_entry_bytes:
            raise ValueError(f"Entry {entry.id} exceeds classification byte budget")
        if current and (len(current) == 100 or size + item_size > max_bytes):
            yield current
            current, size = [], 0
        current.append(entry)
        size += item_size
    if current:
        yield current


def parse_votes(response: str, count: int) -> list[str]:
    """Require exactly one A/B/C vote for every requested number and no extra text."""
    if not 1 <= count <= 100:
        raise ValueError("Expected 1–100 votes")
    votes = {}
    for line in response.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"\s*(3[0-9]{2})\s+([ABC])\s*", line)
        if match is None or int(match[1]) in votes:
            raise ValueError("Malformed or duplicate classification vote")
        votes[int(match[1])] = match[2]
    if set(votes) != set(range(300, 300 + count)):
        raise ValueError("Classification numbers do not match the request")
    return [votes[number] for number in range(300, 300 + count)]


def consensus(votes: list[str], locales: tuple[str, ...], rare: set[str]) -> dict:
    """Majority, conservative three-way tie, then useful rare-locale protection."""
    if len(votes) != 3 or any(vote not in {"A", "B", "C"} for vote in votes):
        raise ValueError("Three valid model votes are required")
    counts = Counter(votes)
    label = min(counts, key=lambda value: (-counts[value], value))
    reason = "three-way-tie" if len(counts) == 3 else "majority"
    if label == "C" and counts["C"] != 3 and rare.intersection(locales):
        label, reason = "B", "rare-locale-with-useful-model-vote"
    return {"class": label, "reason": reason, "disagreement": len(counts) > 1}
