# this_file: src/vexy_localizzy/catalog_translation_types.py
"""Catalog translation context, dispositions and actual-provider evidence."""

from typing import Literal

from pydantic import Field, field_validator

from vexy_localizzy.catalog import Catalog, Finding
from vexy_localizzy.translation_types import Text, TranslationExample, TranslationRecord


class PromptContext(TranslationRecord):
    style: str = ""
    glossary: dict[str, str] = Field(default_factory=dict)
    examples: list[TranslationExample] = Field(default_factory=list)


class InvariantApproval(TranslationRecord):
    source_hash: Text
    reason: Text

    @field_validator("source_hash", "reason")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Invariant approvals require a source hash and reason")
        return value


class Disposition(TranslationRecord):
    key: str
    status: Literal[
        "excluded_empty",
        "excluded_vanished",
        "reviewed",
        "invariant",
        "candidate",
        "review_required",
        "pending",
        "memory",
        "kept",
    ]
    reason: str = ""


class Prefill(TranslationRecord):
    """Targets decided before any provider call: a memory hit or a kept translation.

    ``values`` uses ``qa_catalog.scalar_targets`` form keys ("scalar", "0", ...).
    """

    values: dict[str, str]
    state: Literal["translated", "needs_review", "approved"]
    status: Literal["memory", "kept"]
    reason: str = ""


class ProviderEvidence(TranslationRecord):
    item_ids: list[str]
    request_sha256: Text
    requested_model: Text
    reported_model: Text


class CatalogTranslation(TranslationRecord):
    template_sha256: Text
    catalog: Catalog
    dispositions: list[Disposition]
    providers: list[ProviderEvidence]
    findings: list[Finding]
    pending_messages: int
    ready: bool
