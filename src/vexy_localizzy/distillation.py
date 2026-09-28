# this_file: src/vexy_localizzy/distillation.py
"""Strict LLM subset selection with majority equivalence and rare-locale guards."""

import json
import math
import re
from collections import Counter, defaultdict
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from vexy_localizzy.embedding_store import validate_vectors
from vexy_localizzy.locales import canonical_locale


class DistillationEntry(BaseModel):
    """One unchanged source and its selected translations, supplied by the caller."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    id: int = Field(gt=0)
    source: str = Field(min_length=1)
    targets: dict[str, str] = Field(min_length=1)
    criticality: Literal["A", "B"]
    quality: int = Field(ge=0)

    @field_validator("targets")
    @classmethod
    def usable_targets(cls, value):
        if any(
            not text.strip() or canonical_locale(locale) != locale
            for locale, text in value.items()
        ):
            raise ValueError("Targets require canonical locales and nonempty text")
        return value


class Replacement(BaseModel):
    """Explicit semantic equivalence to another entry retained in the same vote."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    id: int
    representative: int
    equivalent: bool
    reason: str = Field(min_length=1, max_length=160)


class Selection(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    keep: list[int]
    drop: list[Replacement]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate selection field: {key}")
        result[key] = value
    return result


def parse_selection(response: str, count: int) -> Selection:
    """Require every numbered entry 300..399 exactly once, with direct kept representatives."""
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError("Selection count must be between 1 and 100")
    if len(response.encode()) > 32000:
        raise ValueError("Selection response exceeds reserved byte budget")
    fenced = re.fullmatch(
        r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```", response.strip(), re.DOTALL
    )
    if fenced:
        response = fenced.group(1)
    vote = Selection.model_validate(
        json.loads(response, object_pairs_hook=_unique_object)
    )
    covered = vote.keep + [item.id for item in vote.drop]
    if (
        not vote.keep
        or len(set(covered)) != len(covered)
        or set(covered) != set(range(300, 300 + count))
    ):
        raise ValueError(
            "Selection must cover every known ID exactly once and keep a representative"
        )
    if any(
        not item.equivalent
        or item.representative not in vote.keep
        or not item.reason.strip()
        for item in vote.drop
    ):
        raise ValueError("Every drop requires explicit equivalence to a retained entry")
    return vote


def _coverage(entries):
    return dict(
        sorted(Counter(locale for entry in entries for locale in entry.targets).items())
    )


def decide(
    entries: list[DistillationEntry],
    vectors: np.ndarray,
    responses: dict[str, str],
    *,
    rare_locales: set[str],
    threshold: float = 0.90,
) -> dict:
    """Apply three distinct model responses; missing/invalid votes raise, never approve.

    The caller resolves provider aliases and ensures vectors belong to one verified
    embedding space in the same order as entries. Numbered response IDs are local
    to this batch; the result retains actual source IDs and complete model votes.
    """
    if len(responses) != 3 or any(
        not isinstance(model, str) or not model for model in responses
    ):
        raise ValueError("Exactly three distinct actual model identities are required")
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Similarity threshold must be finite and between zero and one")
    entries = [
        DistillationEntry.model_validate(entry.model_dump()) for entry in entries
    ]
    if len({entry.id for entry in entries}) != len(entries):
        raise ValueError("Duplicate source IDs")
    if any(canonical_locale(locale) != locale for locale in rare_locales):
        raise ValueError("Rare locales must use canonical spelling")
    votes = {
        model: parse_selection(response, len(entries))
        for model, response in sorted(responses.items())
    }
    if np.ndim(vectors) != 2:
        raise ValueError("Expected a matrix of embedding vectors")
    values = validate_vectors(vectors, len(entries), np.shape(vectors)[1]).astype(
        np.float64
    )
    proposals = defaultdict(lambda: defaultdict(list))
    for model, vote in votes.items():
        for item in vote.drop:
            proposals[item.id - 300][item.representative - 300].append(model)
    dropped, overrides = [], []
    for index, candidates in sorted(proposals.items()):
        representative, models = max(
            candidates.items(), key=lambda item: (len(item[1]), -entries[item[0]].id)
        )
        similarity = float(
            np.dot(values[index], values[representative])
            / (np.linalg.norm(values[index]) * np.linalg.norm(values[representative]))
        )
        similarity = min(1.0, max(-1.0, similarity))
        missing = (set(entries[index].targets) & rare_locales) - set(
            entries[representative].targets
        )
        reason = (
            "no_majority_equivalence"
            if len(models) < 2
            else "rare_locale_coverage"
            if missing
            else "similarity"
            if similarity < threshold
            else None
        )
        if reason:
            overrides.append({"source_id": entries[index].id, "reason": reason})
        else:
            dropped.append(
                {
                    "source_id": entries[index].id,
                    "representative_id": entries[representative].id,
                    "similarity": similarity,
                    "models": models,
                }
            )
    removed = {item["source_id"] for item in dropped}
    if any(item["representative_id"] in removed for item in dropped):
        raise ValueError("A proposed representative would also be removed")
    kept = [entry for entry in entries if entry.id not in removed]
    return {
        "kept": [entry.id for entry in kept],
        "dropped": dropped,
        "overrides": overrides,
        "votes": {model: vote.model_dump() for model, vote in votes.items()},
        "coverage_before": _coverage(entries),
        "coverage_after": _coverage(kept),
        "threshold": threshold,
        "rare_locales": sorted(rare_locales),
    }
