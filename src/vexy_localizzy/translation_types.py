# this_file: src/vexy_localizzy/translation_types.py
"""Strict localization batch contracts; cache identities retain all prompt inputs."""

import json
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

from vexy_localizzy.json_values import invalid_constant, unique_object
from vexy_localizzy.locales import canonical_locale

Text = Annotated[str, Field(min_length=1)]


class TranslationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TranslationItem(TranslationRecord):
    """One scalar target, including an explicit plural/length-variant context."""

    id: Text
    source: Text
    context: str = ""
    comment: str = ""
    notes: list[str] = Field(default_factory=list)
    form: str = ""
    max_length: int | None = Field(
        default=None, ge=0, exclude_if=lambda value: value is None
    )

    @field_validator("id", "source")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Translation IDs and source text must be nonempty")
        return value


class TranslationExample(TranslationRecord):
    source: Text
    target: Text
    provenance: Text


class TranslationBatch(TranslationRecord):
    source_lang: Text
    target_lang: Text
    items: Annotated[list[TranslationItem], Field(min_length=1, max_length=100)]
    style: str = ""
    glossary: dict[str, str] = Field(default_factory=dict)
    examples: list[TranslationExample] = Field(default_factory=list)

    @field_validator("source_lang", "target_lang")
    @classmethod
    def language(cls, value):
        return canonical_locale(value)

    @model_validator(mode="after")
    def unique_items(self):
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("Translation message IDs must be distinct")
        if self.source_lang == self.target_lang:
            raise ValueError("Source and target locales must differ")
        return self


class TranslationTarget(TranslationRecord):
    id: Text
    target: Text

    @field_validator("target")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Translated text must be nonempty")
        return value


class TranslationResult(TranslationRecord):
    targets: dict[str, str]
    requested_model: Text
    reported_model: Text
    vocabulary: dict[str, str] = Field(default_factory=dict)

    @field_validator("requested_model", "reported_model")
    @classmethod
    def nonblank_model(cls, value):
        if not value.strip():
            raise ValueError("Translation model identity must be nonblank")
        return value


def parse_targets(text: str, batch: TranslationBatch) -> dict[str, str]:
    """Require one nonempty target per original ID, with no duplicates or extras."""
    rows = TypeAdapter(list[TranslationTarget]).validate_python(
        json.loads(
            text, object_pairs_hook=unique_object, parse_constant=invalid_constant
        )
    )
    targets = {row.id: row.target for row in rows}
    ids = [item.id for item in batch.items]
    if len(rows) != len(ids) or len(targets) != len(rows) or set(targets) != set(ids):
        raise ValueError(
            "Translation response must cover every message ID exactly once"
        )
    return {key: targets[key] for key in ids}


def check_result(
    result: TranslationResult, batch: TranslationBatch, model: str
) -> None:
    """Revalidate transport/cache results instead of trusting constructed model objects."""
    result = TranslationResult.model_validate(result.model_dump())
    if result.requested_model != model:
        raise ValueError("Translation response belongs to another requested model")
    parse_targets(
        json.dumps(
            [{"id": key, "target": value} for key, value in result.targets.items()]
        ),
        batch,
    )
