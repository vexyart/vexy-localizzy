# this_file: src/vexy_localizzy/memory/glossary.py
"""Core terminology memory: term selection for prompts and whole-string term hits.

A glossary TMX has tuid ``term:<id>`` with props ``x-term-id``, ``x-category``,
``x-translatable`` (yes/no), ``x-status`` (approved/proposed/do-not-translate) and,
optionally, ``x-fallback``: the fallback original term, a plain English phrase
to translate when the term itself will not travel (``stem`` carries ``main
stroke``, ``overshoot`` carries ``optical surplus``). The TU note is the English
definition; the target TUV may carry a translator note.
"""

import re
import unicodedata
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Literal

from vexy_localizzy.catalog import PLACEHOLDER_PATTERNS, Record
from vexy_localizzy.memory.direct import BilingualFile, read_bilingual

DEFAULT_STATUSES = frozenset({"approved", "do-not-translate"})
# Languages whose lowercase i capitalizes to the dotted İ.
DOTTED_CAPITAL_I = frozenset({"tr", "az"})
TAG = re.compile(r"<[^>]+>")
ACCELERATOR = re.compile(r"&&|&(?=\w)")
ACCELERATOR_SUFFIX = re.compile(
    r"[ \t]*(?:\(&[A-Za-z0-9]\)|（&[A-Za-z0-9]）)(?=[ \t]*(?:…|\.{3}|[:：])?[ \t]*$)"
)
PLACEHOLDER = re.compile(
    "|".join(
        [r"%L\d+|%n"]
        + [PLACEHOLDER_PATTERNS[k].pattern for k in ("qt", "printf", "python_brace")]
    )
)


class Term(Record):
    """One glossary entry for the selected target language."""

    term_id: str
    tuid: str
    source: str
    target: str
    status: Literal["approved", "proposed", "do-not-translate"] | None
    translatable: bool
    note: str | None = None
    target_note: str | None = None
    fallback: str | None = None

    @property
    def rendering(self) -> str:
        """What a translation must use: the source itself when not translatable."""
        if not self.translatable or self.status == "do-not-translate":
            return self.source
        return self.target

    @property
    def hint(self) -> str:
        """The prompt rendering: the target when there is one, otherwise the
        fallback original term marked as such, so the engine translates the
        plain phrase instead of inventing a term for the empty target."""
        if (
            self.translatable
            and self.status != "do-not-translate"
            and not self.target.strip()
        ):
            if self.fallback:
                return f"(translate the plain phrase: {self.fallback})"
        return self.rendering

    def label(self, source: str, lang: str | None = None) -> str:
        """The rendering for a message whose whole text is this term.

        A glossary holds dictionary forms, so a target is capitalized when the
        message starts with an uppercase letter (after the tags and mnemonic
        marker that matching ignores). A term that is not translated keeps the
        glossary spelling.
        """
        if not self.translatable or self.status == "do-not-translate":
            return self.rendering
        if plain_text(source)[:1].isupper():
            return capitalize_first(self.rendering, lang)
        return self.rendering


def plain_text(text: str) -> str:
    """NFC → drop tags and appended Qt shortcut annotations → drop single '&'
    accelerators (keep '&&' as '&')
    → replace Qt/printf/brace placeholders with a space; case is kept."""
    text = TAG.sub("", unicodedata.normalize("NFC", text))
    text = ACCELERATOR_SUFFIX.sub("", text)
    text = ACCELERATOR.sub(lambda m: "&" if m.group() == "&&" else "", text)
    return PLACEHOLDER.sub(" ", text)


def match_text(text: str) -> str:
    """``plain_text``, casefolded: the key that term matching compares."""
    return plain_text(text).casefold()


def capitalize_first(text: str, lang: str | None = None) -> str:
    """``text`` with its first character capitalized, if it is a lowercase letter
    that has a one-letter capital.

    Text in a script without case, text that starts with a digit, quote or
    space, and a letter without a single capital (``ß``) come back unchanged.
    Title case is used, so Georgian (capitals only in all-caps text) is left
    alone. ``lang`` adds two spelling rules: Turkish and Azerbaijani ``i``
    becomes ``İ``, and the Dutch digraph ``ij`` becomes ``IJ``.
    Referenced by ``translate.run`` for whole-string term hits.
    """
    first = text[:1]
    if not first.islower():
        return text
    code = (lang or "").replace("_", "-").split("-")[0].lower()
    if code in DOTTED_CAPITAL_I and first == "i":
        return "İ" + text[1:]
    if code == "nl" and text.startswith("ij"):
        return "IJ" + text[2:]
    capital = first.title()
    return capital + text[1:] if len(capital) == 1 and capital != first else text


def _term(unit, src, tgt) -> Term:
    props: dict[str, str] = {}
    for name, value in unit.properties:
        props.setdefault(name, value)
    return Term(
        term_id=props.get("x-term-id") or unit.tuid.removeprefix("term:"),
        tuid=unit.tuid,
        source=src.text,
        target=tgt.text,
        status=props.get("x-status") or None,
        translatable=props.get("x-translatable", "yes") != "no",
        note=unit.notes[0] if unit.notes else None,
        target_note=tgt.notes[0] if tgt.notes else None,
        fallback=props.get("x-fallback") or None,
    )


class Glossary:
    """Terms filtered by status; the first file wins for a repeated source."""

    def __init__(self, files: Sequence[BilingualFile], statuses: frozenset[str]):
        self.files = tuple(files)
        self.statuses = statuses
        self.excluded = 0
        self.terms: list[Term] = []
        self._patterns: list[tuple[Term, re.Pattern[str]]] = []
        self._whole: dict[str, Term] = {}
        for file in self.files:
            for unit, src, tgt in file.pairs:
                # Filter on the raw status first: an unknown value such as
                # "deprecated" is excluded, not a reason to abort the whole load.
                raw = next((v for n, v in unit.properties if n == "x-status"), None)
                key = match_text(src.text)
                if (raw or None) not in statuses or not key.strip():
                    self.excluded += 1
                    continue
                term = _term(unit, src, tgt)
                if key in self._whole:
                    continue
                self._whole[key] = term
                self.terms.append(term)
                pattern = re.compile(rf"(?<!\w){re.escape(key)}(?!\w)")
                self._patterns.append((term, pattern))

    @classmethod
    def load(
        cls,
        paths: Sequence[Path],
        *,
        source_lang: str,
        target_lang: str,
        memory_lang: str | None = None,
        statuses: frozenset[str] = DEFAULT_STATUSES,
    ) -> "Glossary":
        files = [
            read_bilingual(
                path,
                source_lang=source_lang,
                target_lang=target_lang,
                memory_lang=memory_lang,
            )
            for path in paths
        ]
        return cls(files, frozenset(statuses))

    def relevant(self, texts: Iterable[str], *, limit: int = 60) -> dict[str, str]:
        """Terms occurring in any text, longest sources first past `limit`,
        returned in casefolded source order so prompt cache keys stay stable."""
        haystacks = [match_text(text) for text in texts]
        found = [
            term
            for term, pattern in self._patterns
            if any(pattern.search(text) for text in haystacks)
        ]
        if len(found) > limit:
            found.sort(key=lambda t: (-len(t.source), t.source.casefold(), t.source))
            found = found[:limit]
        selected = {term.source: term.hint for term in found}
        return dict(sorted(selected.items(), key=lambda kv: (kv[0].casefold(), kv[0])))

    def whole_match(self, text: str) -> Term | None:
        """The term whose whole match text equals this text's, for the `term` class."""
        return self._whole.get(match_text(text))

    def summary(self) -> dict:
        return {
            "files": [f.path for f in self.files],
            "sha256": {f.path: f.sha256 for f in self.files},
            "tus_total": sum(f.total for f in self.files),
            "tus_skipped": sum(f.skipped for f in self.files),
            "terms": len(self.terms),
            "terms_excluded": self.excluded,
            "statuses": sorted(self.statuses),
            "languages": {
                f.path: {"source": f.source_lang, "target": f.target_lang}
                for f in self.files
            },
        }
