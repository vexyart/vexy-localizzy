# this_file: src/vexy_localizzy/review_types.py
"""Strict edit and journal contracts for the local catalog reviewer."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, TypeAdapter

from vexy_localizzy.catalog import Catalog, Record

Revision = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ReviewConflict(RuntimeError):
    """Saved revision or interrupted transaction conflicts with current disk state."""


class ReviewEdit(Record):
    model_config = ConfigDict(strict=True)
    key: str
    revision: Revision
    targets: dict[str, str]
    action: Literal["draft", "approve"] = "draft"
    reason: str = ""


class ReviewSnapshot(Record):
    revision: Revision
    catalog: Catalog


class Intent(Record):
    kind: Literal["intent"] = "intent"
    id: str
    old: Revision
    new: Revision
    edit: ReviewEdit


class Completion(Record):
    kind: Literal["complete"] = "complete"
    id: str
    status: Literal["applied", "unapplied"]


JOURNAL_ROW = TypeAdapter(Annotated[Intent | Completion, Field(discriminator="kind")])
