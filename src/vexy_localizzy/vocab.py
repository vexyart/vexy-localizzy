# this_file: src/vexy_localizzy/vocab.py
"""A keyed multilingual vocabulary corpus as a catalog: load, validate, export, stats.

A corpus is one object keyed by message key. An entry is bilingual
(``en``/``de``/… plus ``context``) or metadata (``translation`` plus
``context``). Two physical forms are read: a JSON file, and a JavaScript data
file of the shape ``const name = {...};`` with ``//`` comments, as a small
browser viewer loads it. A reviewed corpus is a golden set: fixtures for
tests and a reference for benchmarks, so ``validate`` is itself a QA pass.
Referenced by ``localizzy vocab``.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from vexy_localizzy.catalog import Catalog, Finding, Unit, detect_placeholders
from vexy_localizzy.formats import json_io
from vexy_localizzy.plurals import parse_icu_plural

LOCALE_KEY = re.compile(r"[a-z]{2,3}(?:-[A-Za-z0-9]+)*")  # de, pt-BR, zh-Hant
# A string literal (kept), a // comment (dropped) or a trailing comma (dropped).
_JS_NOISE = re.compile(r'(?P<string>"(?:[^"\\]|\\.)*")|//[^\n]*|,(?=\s*[}\]])')
NON_LOCALE_FIELDS = ("context", "translation")
DISAMBIGUATION_MARK = ".disambig."


@dataclass(frozen=True)
class VocabStats:
    total: int
    families: dict[str, int] = field(default_factory=dict)
    placeholder_kinds: dict[str, int] = field(default_factory=dict)
    plural_units: int = 0
    disambiguation_units: int = 0
    locale_coverage: dict[str, int] = field(default_factory=dict)


def _js_to_json(text: str) -> str:
    """Turn ``const x = { ... };`` with ``//`` comments into a JSON object string.

    Comments and trailing commas are removed outside string literals only, so a
    URL inside a value survives.
    """
    body = text[text.index("{") :].rstrip().rstrip(";")
    return _JS_NOISE.sub(lambda m: m.group("string") or "", body)


def load_raw(path: str | Path) -> dict[str, dict]:
    """The corpus object from a ``.json`` or JavaScript data file."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return json.loads(text if path.suffix == ".json" else _js_to_json(text))


def _disambiguation(key: str) -> str | None:
    """The hint carried by a ``….disambig.<hint>`` key, for example ``kern noun``."""
    if DISAMBIGUATION_MARK not in key:
        return None
    return key.split(DISAMBIGUATION_MARK, 1)[1].replace(".", " ")


def load(
    path: str | Path, *, locale: str | None = None, source_locale: str = "en"
) -> Catalog:
    """The corpus as a source catalog, or a bilingual one when ``locale`` is given."""
    units: list[Unit] = []
    for key, entry in load_raw(path).items():
        context = entry.get("context", "")
        source = entry.get(source_locale) or entry.get("translation") or ""
        target = entry.get(locale) if locale else None
        plural = parse_icu_plural(source)
        if plural is not None and target:
            plural = parse_icu_plural(target) or plural
        units.append(
            Unit(
                key=key,
                context=context,
                source=source,
                target=target,
                disambiguation=_disambiguation(key),
                notes=[context] if context else [],
                plural=plural,
                placeholders=detect_placeholders(source),
                state="translated" if target else "untranslated",
            )
        )
    return Catalog(
        source_lang=source_locale, target_lang=locale, units=units, origin_format="json"
    )


def available_locales(path: str | Path, *, source_locale: str = "en") -> list[str]:
    """Locale codes present across the bilingual entries of the corpus."""
    skip = (*NON_LOCALE_FIELDS, source_locale)
    return sorted(
        {
            name
            for entry in load_raw(path).values()
            for name in entry
            if name not in skip and LOCALE_KEY.fullmatch(name)
        }
    )


def export(out: str | Path, path: str | Path, *, locale: str | None = None) -> Catalog:
    """Write the corpus as canonical catalog JSON, a fixture other commands read."""
    catalog = load(path, locale=locale)
    json_io.dump(catalog, out)
    return catalog


def stats(path: str | Path) -> VocabStats:
    """Counts by key family, placeholder kind, plural and disambiguation, and locale."""
    raw = load_raw(path)
    catalog = load(path)
    families: dict[str, int] = {}
    for key in raw:
        family = key.split(".", 1)[0]
        families[family] = families.get(family, 0) + 1
    kinds: dict[str, int] = {}
    for unit in catalog.units:
        for placeholder in unit.placeholders:
            kinds[placeholder.kind] = kinds.get(placeholder.kind, 0) + 1
    return VocabStats(
        total=len(catalog.units),
        families=dict(sorted(families.items())),
        placeholder_kinds=kinds,
        plural_units=sum(1 for unit in catalog.units if unit.plural),
        disambiguation_units=sum(1 for unit in catalog.units if unit.disambiguation),
        locale_coverage={
            locale: sum(1 for entry in raw.values() if entry.get(locale))
            for locale in available_locales(path)
        },
    )


def validate(path: str | Path) -> list[Finding]:
    """Corpus invariants: every entry has context, every ICU plural has ``other``."""
    findings: list[Finding] = []
    for unit in load(path).units:
        if not unit.context:
            findings.append(
                Finding(
                    rule_id="VOCAB-CONTEXT",
                    severity="major",
                    message="Entry has no context.",
                    unit_key=unit.key,
                )
            )
        if unit.plural and "other" not in unit.plural.forms:
            findings.append(
                Finding(
                    rule_id="VOCAB-PLURAL",
                    severity="major",
                    message="ICU plural lacks the mandatory 'other' category.",
                    unit_key=unit.key,
                )
            )
    return findings


def flat(path: str | Path, *, locale: str | None = None) -> dict[str, str]:
    """The corpus as a flat ``{key: text}`` mapping: sources, or one locale's targets.

    This is the shape ``translate_json`` reads and writes, so a benchmark run is
    ``vocab export --flat``, ``translate_json``, ``vocab compare``.
    """
    units = load(path, locale=locale).units
    return {
        unit.key: (unit.target if locale else unit.source) or ""
        for unit in units
        if (unit.target if locale else unit.source)
    }


def compare(path: str | Path, candidate: Catalog | dict[str, str], locale: str) -> dict:
    """Score a candidate catalog against the corpus references for ``locale``.

    The corpus is the golden set: translate its export with any engine, then
    compare. Only entries with a reference in ``locale`` count. The result lists
    the keys the candidate lacks and every differing pair, so a benchmark run
    shows what changed and not only a rate.
    """
    references = {
        unit.key: unit.target for unit in load(path, locale=locale).units if unit.target
    }
    if not references:
        raise ValueError(f"The corpus has no {locale!r} references")
    targets = (
        candidate
        if isinstance(candidate, dict)
        else {unit.key: unit.target for unit in candidate.units}
    )
    missing = sorted(key for key in references if not targets.get(key))
    different = [
        {"key": key, "reference": reference, "candidate": targets[key]}
        for key, reference in references.items()
        if targets.get(key) and targets[key] != reference
    ]
    exact = len(references) - len(missing) - len(different)
    return {
        "locale": locale,
        "total": len(references),
        "exact": exact,
        "exact_rate": round(exact / len(references), 4),
        "missing": missing,
        "different": different,
    }
