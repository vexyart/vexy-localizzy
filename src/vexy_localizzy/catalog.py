# this_file: src/vexy_localizzy/catalog.py
"""Versioned catalog types; compatibility fields adapted from earlier tooling (see NOTICE)."""

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from vexy_localizzy.formats.document import SourceDocument

PlaceholderStyle = Literal["qt", "printf", "python_brace", "icu", "i18next", "html"]
PlaceholderKind = Literal["arg", "tag", "accelerator", "numerus"]
UnitState = Literal[
    "untranslated", "needs_review", "translated", "approved", "vanished"
]
Severity = Literal["info", "minor", "major", "critical"]
# "fl10n" is the legacy name of "localizzy" in catalog JSON written before 1.1.
OriginFormat = Literal[
    "ts", "po", "xliff", "json", "android", "localizzy", "fl10n", "tmx", "i18next"
]


class Record(BaseModel):
    """Reject unknown serialized fields instead of silently dropping data."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Placeholder(Record):
    """A placeholder token and its syntax."""

    token: str
    style: PlaceholderStyle
    kind: PlaceholderKind = "arg"
    note: str | None = None


class PluralForms(Record):
    """Explicit category or positional forms, with optional length variants.

    Qt and gettext positions use decimal keys and ``indexing='index'``.
    They are never inferred to be CLDR categories. For a variant-bearing form,
    the first variant must equal its entry in ``forms``.
    """

    icu: str | None = None
    forms: dict[str, str] = Field(default_factory=dict)
    indexing: Literal["cldr", "index"] = "cldr"
    variants: dict[str, list[str]] = Field(default_factory=dict)


class Unit(Record):
    """One message; record_id binds an edit to its retained source document."""

    key: str
    context: str
    source: str
    source_plural: str | None = None
    target: str | None = None
    disambiguation: str | None = None
    notes: list[str] = Field(default_factory=list)
    plural: PluralForms | None = None
    placeholders: list[Placeholder] = Field(default_factory=list)
    max_length: int | None = None
    locations: list[str] = Field(default_factory=list)
    state: UnitState = "untranslated"
    source_hash: str = ""
    record_id: str | None = None
    variants: list[str] | None = None

    def model_post_init(self, _ctx: object) -> None:
        if not self.source_hash:
            object.__setattr__(self, "source_hash", compute_source_hash(self))


class Catalog(Record):
    """Editable messages plus the complete original-format document."""

    schema_version: Literal[1] = 1
    source_lang: str
    target_lang: str | None = None
    units: list[Unit] = Field(default_factory=list)
    origin_format: OriginFormat = "localizzy"
    document: SourceDocument | None = None


class Finding(Record):
    """A conversion or QA finding with stable machine-readable identity."""

    rule_id: str
    severity: Severity
    message: str
    unit_key: str | None = None
    location: str | None = None
    confidence: Literal["exact", "heuristic"] = "exact"
    data: dict = Field(default_factory=dict)


def compute_source_hash(unit: Unit) -> str:
    """Hash source, context and disambiguation for existing consumer caches."""
    payload = f"{unit.source}\x00{unit.context}\x00{unit.disambiguation or ''}"
    if unit.source_plural is not None:
        payload += "\x00" + unit.source_plural
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def slug(text: str) -> str:
    """Legacy key stem; format readers separately disambiguate collisions."""
    out = re.sub(r"[^\w]+", "_", text.strip().lower()).strip("_")
    return out[:40] or "_"


def derive_key(context: str, source: str, disambiguation: str | None = None) -> str:
    """Keep the legacy key convention for messages without explicit IDs."""
    parts = [context or "_", slug(source)]
    if disambiguation:
        parts.append(slug(disambiguation))
    return ".".join(parts)


PLACEHOLDER_PATTERNS: dict[str, re.Pattern[str]] = {
    "qt": re.compile(r"%\d+"),
    "printf": re.compile(r"%\([\w]+\)[sdifeg]|%[sdifeg]"),
    "python_brace": re.compile(r"\{\w+\}"),
    "i18next": re.compile(r"\{\{[\w.]+\}\}"),
    "icu": re.compile(r"\{\s*\w+\s*(?:,[^{}]*)?\}"),
    "html": re.compile(r"<[^>]+>"),
}


def detect_placeholders(text: str) -> list[Placeholder]:
    """Legacy best-effort inventory; full translation QA is a separate gate."""
    found: list[Placeholder] = []
    for style in ("icu", "i18next", "qt", "printf", "python_brace"):
        matches = list(PLACEHOLDER_PATTERNS[style].finditer(text))
        if matches:
            found.extend(
                Placeholder(
                    token=token,
                    style=style,
                    kind="numerus" if style == "icu" else "arg",
                )
                for token in dict.fromkeys(m.group() for m in matches)
            )
            break
    found.extend(
        Placeholder(token=m.group(), style="html", kind="tag")
        for m in PLACEHOLDER_PATTERNS["html"].finditer(text)
    )
    return found
