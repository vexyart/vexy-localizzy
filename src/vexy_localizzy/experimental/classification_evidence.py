# this_file: src/vexy_localizzy/experimental/classification_evidence.py
"""Version-one classification evidence schemas and saved model identity checks."""

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from vexy_localizzy.experimental.classification import consensus
from vexy_localizzy.experimental.classification_models import model_chains

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
PositiveId = Annotated[int, Field(gt=0, lt=2**63)]
Count = Annotated[int, Field(ge=0)]
Label = Literal["A", "B", "C"]


class Evidence(BaseModel):
    model_config = ConfigDict(strict=True)


class InputMetadata(Evidence):
    type: Literal["metadata"]
    version: Annotated[int, Field(ge=1, le=1)]
    entries: Count
    source_snapshot: Digest
    entry_map_sha256: Digest | None = None
    coverage: dict[str, Count]


class InputEntry(Evidence):
    id: PositiveId
    text: str
    locales: list[str]


class RunIdentity(Evidence):
    input_sha256: Digest
    source_snapshot: Digest
    prompt_sha256: Digest
    models: list[str]
    fallbacks: dict[str, list[str]] = Field(default_factory=dict)
    model_identities: dict[str, str] = Field(default_factory=dict)
    rare_threshold: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    consensus_version: Annotated[int, Field(ge=1, le=1)]


class Complete(Evidence):
    run_id: Digest
    decision_sha256: Digest
    entries: Count
    expected_entries: Count
    pending_entries: Annotated[int, Field(ge=0, le=0)]
    complete: bool
    classes: dict[Label, Count]
    rare_locales: list[str]


def checked_models(row, identity: RunIdentity, chains) -> bool:
    """Keep unknown reports unknown; configured aliases may resolve old responses."""
    models, requested, reported = (
        json.loads(row[k]) for k in ("models", "requested_models", "reported_models")
    )
    if requested != identity.models or not all(
        isinstance(values, list) and len(values) == 3 for values in (models, reported)
    ):
        raise ValueError("Classification model evidence does not match the run")
    if any(not isinstance(m, str) or m not in chains[i] for i, m in enumerate(models)):
        raise ValueError("Classification used a model outside its fallback policy")
    if any(m is not None and (not isinstance(m, str) or not m) for m in reported):
        raise ValueError("Invalid provider-reported model identity")
    resolved = [
        r or identity.model_identities.get(m)
        for m, r in zip(models, reported, strict=True)
    ]
    if (
        row["identity_verified"] != 1
        or None in resolved
        or len(set(resolved)) != 3
        or len(set(models)) != 3
    ):
        raise ValueError(
            "Classification requires three distinct resolved model identities"
        )
    return all(m is not None for m in reported)


def check_decision(row, entry: InputEntry, rare: set[str]) -> None:
    votes = json.loads(row["votes"])
    if not isinstance(votes, list):
        raise ValueError("Classification votes must be a list")
    decision = consensus(votes, tuple(entry.locales), rare)
    if any(row[key] != value for key, value in decision.items()):
        raise ValueError(
            f"Classification decision {entry.id} disagrees with its votes/policy"
        )


def policy(identity: RunIdentity, metadata: InputMetadata):
    """Use the original version-one fallback and rarity rules."""
    chains = model_chains(identity.models, identity.fallbacks)
    candidates = {m for chain in chains for m in chain}
    if set(identity.model_identities) - candidates or any(
        not v for v in identity.model_identities.values()
    ):
        raise ValueError("Invalid configured model identities")
    rare = {
        locale
        for locale, count in metadata.coverage.items()
        if count < max(metadata.coverage.values(), default=0) * identity.rare_threshold
    }
    return chains, rare
