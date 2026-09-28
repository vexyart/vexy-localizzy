# this_file: src/vexy_localizzy/memory/direct.py
"""Verbatim lookup in a direct (project UI) translation memory.

A direct memory holds reviewed catalog messages as TMX: tuid ``Context|Source[:form]``
with props ``x-context``, ``x-comment``, ``x-numerus-form`` and ``x-message-id``.
Matching is exact after NFC and newline normalization; loose matching is not done here.
"""

import hashlib
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from vexy_localizzy.catalog import Finding, Record, Unit
from vexy_localizzy.memory.langmatch import select_language
from vexy_localizzy.tmx import Segment, read_tmx
from vexy_localizzy.tmx import Unit as TmxUnit

MatchClass = Literal["id", "context", "source", "term"]
RANK: dict[str, int] = {"source": 1, "context": 2, "id": 3}


class MemoryEntry(Record):
    """One memory TU reduced to the selected source and target texts."""

    memory: str
    memory_sha256: str
    tuid: str
    ordinal: int
    source: str
    target: str
    context: str | None = None
    comment: str | None = None
    message_id: str | None = None
    form: int | None = None


class MemoryHit(Record):
    """Target texts keyed like ``qa_catalog.scalar_targets`` ("scalar", "0", …)."""

    match: MatchClass
    values: dict[str, str]
    entries: tuple[MemoryEntry, ...]


@dataclass(frozen=True)
class BilingualFile:
    """A memory file read whole, with its selected source and target languages."""

    path: str
    sha256: str
    source_lang: str
    target_lang: str
    pairs: tuple[tuple[TmxUnit, Segment, Segment], ...]
    total: int
    skipped: int


def normalize_source(text: str) -> str:
    """Verbatim-match key: NFC and CRLF→LF only; everything else stays significant."""
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n")


def read_bilingual(
    path: str | Path,
    *,
    source_lang: str,
    target_lang: str,
    memory_lang: str | None = None,
) -> BilingualFile:
    """Select languages for one file, then pair source and target segments.

    TUs without both selected variants are counted as skipped, never guessed.
    """
    sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    units = list(read_tmx(path))
    languages = {segment.language for unit in units for segment in unit.segments}
    if not units:
        return BilingualFile(str(path), sha, "", "", (), 0, 0)
    source = select_language(languages, source_lang)
    target = select_language(languages - {source}, target_lang, override=memory_lang)
    pairs = []
    for unit in units:
        src = next((s for s in unit.segments if s.language == source), None)
        tgt = next((s for s in unit.segments if s.language == target), None)
        if src is not None and tgt is not None:
            pairs.append((unit, src, tgt))
    return BilingualFile(
        str(path),
        sha,
        source,
        target,
        tuple(pairs),
        len(units),
        len(units) - len(pairs),
    )


def _entry(file: BilingualFile, unit: TmxUnit, src: Segment, tgt: Segment):
    props: dict[str, str] = {}
    for name, value in unit.properties:
        props.setdefault(name, value)
    form = props.get("x-numerus-form")
    return MemoryEntry(
        memory=file.path,
        memory_sha256=file.sha256,
        tuid=unit.tuid,
        ordinal=unit.ordinal,
        source=src.text,
        target=tgt.text,
        context=props.get("x-context") or None,
        comment=props.get("x-comment") or None,
        message_id=props.get("x-message-id") or None,
        form=int(form) if form is not None else None,
    )


def _values(entries, forms: int | None) -> tuple[dict[str, str] | None, str | None]:
    """Target values of one group, or the problem ("conflict"/"shape") preventing it."""
    if forms is None:
        targets = {e.target for e in entries}
        if len(targets) != 1:
            return None, "conflict"
        return {"scalar": targets.pop()}, None
    by_form: dict[str, str] = {}
    for e in entries:
        if by_form.setdefault(str(e.form), e.target) != e.target:
            return None, "conflict"
    if set(by_form) != {str(i) for i in range(forms)}:
        return None, "shape"
    return {str(i): by_form[str(i)] for i in range(forms)}, None


def _resolve(entries, context, message_id, forms):
    """Best hit within one file, else the problems met: [(kind, entries)]."""
    problems = []

    def tier(match, chosen):
        if not chosen:
            return None
        values, problem = _values(chosen, forms)
        if problem:
            problems.append((problem, chosen))
            return None
        return MemoryHit(match=match, values=values, entries=tuple(chosen))

    if message_id is not None:
        hit = tier("id", [e for e in entries if e.message_id == message_id])
        if hit:
            return hit, problems
    if context is not None:
        hit = tier("context", [e for e in entries if (e.context, e.comment) == context])
        if hit:
            return hit, problems
    groups: dict[tuple, list[MemoryEntry]] = {}
    for e in entries:
        groups.setdefault((e.context, e.comment, e.message_id), []).append(e)
    results = [_values(group, forms) for group in groups.values()]
    for (_, problem), group in zip(results, groups.values(), strict=True):
        if problem:
            problems.append((problem, group))
    if not problems and len({tuple(v.items()) for v, _ in results}) == 1:
        return MemoryHit(
            match="source", values=results[0][0], entries=tuple(entries)
        ), []
    if not problems:
        problems.append(("conflict", entries))
    return None, problems


class DirectMemory:
    """Exact-source lookup over one or more direct memories, first file first."""

    def __init__(self, files: Sequence[BilingualFile]) -> None:
        self.files = tuple(files)
        self.conflicts: list[Finding] = []
        self.variant_units_skipped = 0
        self._indexes: list[dict[str, list[MemoryEntry]]] = []
        for file in self.files:
            index: dict[str, list[MemoryEntry]] = {}
            for unit, src, tgt in file.pairs:
                entry = _entry(file, unit, src, tgt)
                index.setdefault(normalize_source(entry.source), []).append(entry)
            self._indexes.append(index)

    @classmethod
    def load(
        cls,
        paths: Sequence[Path],
        *,
        source_lang: str,
        target_lang: str,
        memory_lang: str | None = None,
    ) -> "DirectMemory":
        return cls(
            [
                read_bilingual(
                    path,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    memory_lang=memory_lang,
                )
                for path in paths
            ]
        )

    def lookup(self, unit: Unit, *, form_count: int | None = None) -> MemoryHit | None:
        """Match a catalog unit; `form_count` overrides the unit's native form count."""
        if unit.variants or (unit.plural is not None and unit.plural.variants):
            self.variant_units_skipped += 1
            return None
        forms = None
        if unit.plural is not None:
            if unit.plural.indexing != "index":
                return None
            forms = form_count if form_count is not None else len(unit.plural.forms)
        message_id = unit.key[3:] if unit.key.startswith("id:") else None
        context = (unit.context or None, unit.disambiguation or None)
        return self._lookup(unit.source, context, message_id, forms, unit.key)

    def lookup_text(
        self, source: str, context: str | None = None, comment: str | None = None
    ) -> str | None:
        """Scalar target for callers without a Unit; no context goes to source tier."""
        wanted = None if context is None else (context or None, comment or None)
        hit = self._lookup(source, wanted, None, None, None)
        return hit.values["scalar"] if hit else None

    def _lookup(self, source, context, message_id, forms, unit_key):
        key = normalize_source(source)
        numerus = forms is not None
        best, problems = None, []
        for index in self._indexes:
            entries = [e for e in index.get(key, ()) if (e.form is not None) == numerus]
            if not entries:
                continue
            hit, found = _resolve(entries, context, message_id, forms)
            problems.extend(found)
            if hit and (best is None or RANK[hit.match] > RANK[best.match]):
                best = hit
        if best is None:
            self._report(problems, source, unit_key, forms)
        return best

    def _report(self, problems, source, unit_key, forms) -> None:
        for kind in ("conflict", "shape"):
            tuids = [e.tuid for k, group in problems if k == kind for e in group]
            if not tuids:
                continue
            self.conflicts.append(
                Finding(
                    rule_id="MEMORY-CONFLICT"
                    if kind == "conflict"
                    else "MEMORY-PLURAL-SHAPE",
                    severity="info",
                    message=(
                        f"memory targets disagree for {source!r}"
                        if kind == "conflict"
                        else f"memory plural forms do not cover 0..{(forms or 0) - 1} for {source!r}"
                    ),
                    unit_key=unit_key,
                    data={"tuids": list(dict.fromkeys(tuids))},
                )
            )

    def summary(self) -> dict:
        return {
            "files": [f.path for f in self.files],
            "sha256": {f.path: f.sha256 for f in self.files},
            "tus_total": sum(f.total for f in self.files),
            "tus_loaded": sum(len(f.pairs) for f in self.files),
            "tus_skipped": sum(f.skipped for f in self.files),
            "languages": {
                f.path: {"source": f.source_lang, "target": f.target_lang}
                for f in self.files
            },
            "variant_units_skipped": self.variant_units_skipped,
        }
