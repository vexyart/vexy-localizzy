# this_file: src/vexy_localizzy/translate/run.py
"""`localizzy translate`: kept targets, direct and glossary memory, then the engine.

Order of decision for each eligible unit:
1. kept: same-language catalog with ``keep_existing`` and a complete existing target;
2. memory: the best memory hit that passes the placeholder QA gate, in the order
   id > context > term > source (``PRECEDENCE``);
3. engine: validated, cached batches through ``translate_catalog``;
4. pending: no engine, or no validated result yet.
Every unit's origin goes into the JSON report sidecar.
"""

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from langcodes import Language
from lxml import etree
from pydantic import Field

from vexy_localizzy.catalog import Catalog, Finding, Record, Unit
from vexy_localizzy.catalog_translation import translate_catalog
from vexy_localizzy.catalog_translation_inputs import fill_unit, item_id
from vexy_localizzy.catalog_translation_types import Prefill
from vexy_localizzy.conversion import convert_catalog, load_any
from vexy_localizzy.formats import qt_numerus, ts, ts_splice
from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.formats.ts_read import load_bytes
from vexy_localizzy.formats.ts_template import prepare_translation
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.direct import DirectMemory, MatchClass
from vexy_localizzy.memory.glossary import DEFAULT_STATUSES, Glossary
from vexy_localizzy.qa import TextPolicy, check_text
from vexy_localizzy.qa_catalog import scalar_targets, shape_findings
from vexy_localizzy.translate.context import GlossaryContext
from vexy_localizzy.translate.engine import EngineSpec, Request, open_cache

PRECEDENCE: tuple[MatchClass, ...] = ("id", "context", "term", "source")
BLOCKING = ("major", "critical")
VALIDATION_IDENTITY = "localizzy-translate:1"
Origin = Literal["kept", "memory", "engine", "pending", "excluded"]


class MemoryPolicy(Record):
    """Which memory match classes are used, and which of them finish a message.

    A hit of a used class outside ``finish_on`` is written unfinished (Qt
    ``type="unfinished"``, state ``needs_review``).
    """

    finish_on: frozenset[MatchClass] = frozenset({"id", "context", "term"})
    use: frozenset[MatchClass] = frozenset({"id", "context", "source", "term"})


class UnitProvenance(Record):
    """Where one message's output came from."""

    key: str
    context: str
    source_sha256: str
    origin: Origin
    match: MatchClass | None = None
    memory: str | None = None
    memory_sha256: str | None = None
    tuids: tuple[str, ...] = ()
    glossary_terms: tuple[str, ...] = ()
    requested_model: str | None = None
    reported_model: str | None = None
    request_sha256: str | None = None


class TranslateReport(Record):
    """The JSON sidecar written next to the output catalog."""

    schema_id: Literal["localizzy-translate/1"] = "localizzy-translate/1"
    catalog: str
    catalog_sha256: str
    out: str
    source_lang: str
    target_lang: str
    memories: list[dict] = Field(default_factory=list)
    counts: dict[str, int]
    units: list[UnitProvenance]
    findings: list[Finding]
    ready: bool


def _eligible(unit: Unit) -> bool:
    return unit.state != "vanished" and bool(unit.source.strip())


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _blocking(unit: Unit, values: dict[str, str], qa: TextPolicy) -> list[Finding]:
    """Major/critical placeholder, markup and accelerator findings for these values."""
    policy = (
        qa.model_copy(update={"max_length": unit.max_length})
        if unit.max_length is not None
        else qa
    )
    return [
        finding
        for form, source, _ in scalar_targets(unit)
        for finding in check_text(
            source, values.get(form), policy=policy, unit_key=unit.key
        )
        if finding.severity in BLOCKING
    ]


def _first_letter(text: str) -> str:
    return next((c for c in text if c.isalpha()), "")


def _match_case(source: str, term_source: str, value: str) -> str:
    """Capitalize a term rendering when the UI label is capitalized and the term
    is not ("Visual kerning" vs term "visual kerning"). Never lowercases."""
    if _first_letter(source).isupper() and _first_letter(term_source).islower():
        index = next((i for i, c in enumerate(value) if c.isalpha()), None)
        if index is not None:
            return value[:index] + value[index].upper() + value[index + 1 :]
    return value


def _candidates(unit: Unit, direct, glossary, term_files):
    """(match, values, tuids, memory path, memory sha) in PRECEDENCE order."""
    found = []
    if direct is not None and (hit := direct.lookup(unit)) is not None:
        first = hit.entries[0]
        tuids = tuple(dict.fromkeys(e.tuid for e in hit.entries))
        found.append(
            (hit.match, dict(hit.values), tuids, first.memory, first.memory_sha256)
        )
    if (
        glossary is not None
        and unit.plural is None
        and unit.variants is None
        and (term := glossary.whole_match(unit.source)) is not None
    ):
        path, sha = term_files.get(term.tuid, (None, None))
        value = _match_case(unit.source, term.source, term.rendering)
        found.append(("term", {"scalar": value}, (term.tuid,), path, sha))
    return sorted(found, key=lambda c: PRECEDENCE.index(c[0]))


def memory_prefill(
    catalog: Catalog,
    *,
    direct: DirectMemory | None,
    glossary: Glossary | None,
    policy: MemoryPolicy,
    qa: TextPolicy,
) -> tuple[dict[str, Prefill], list[UnitProvenance], list[Finding]]:
    """Memory hits for every eligible unit of ``catalog`` that passes the QA gate.

    A hit with a major or critical placeholder, markup or accelerator finding is
    dropped with a ``MEMORY-QA-REJECT`` finding and the next candidate is tried;
    a unit without an acceptable hit is left for the engine.
    """
    term_files = {}
    if glossary is not None:
        for file in glossary.files:
            for tu, _, _ in file.pairs:
                term_files.setdefault(tu.tuid, (file.path, file.sha256))
    before = len(direct.conflicts) if direct is not None else 0
    prefills, provenance, findings = {}, [], []
    for unit in catalog.units:
        if not _eligible(unit):
            continue
        forms = {form for form, _, _ in scalar_targets(unit)}
        for match, values, tuids, memory, sha in _candidates(
            unit, direct, glossary, term_files
        ):
            if match not in policy.use or set(values) != forms:
                continue
            if rejected := _blocking(unit, values, qa):
                findings.append(
                    Finding(
                        rule_id="MEMORY-QA-REJECT",
                        severity="minor",
                        message=f"{match} memory hit rejected by QA: "
                        + ", ".join(sorted({f.rule_id for f in rejected})),
                        unit_key=unit.key,
                        data={"match": match, "tuids": list(tuids)},
                    )
                )
                continue
            name = Path(memory).name if memory else "glossary"
            prefills[unit.key] = Prefill(
                values=values,
                state="translated" if match in policy.finish_on else "needs_review",
                status="memory",
                reason=f"{name}#{tuids[0]} ({match})",
            )
            provenance.append(
                UnitProvenance(
                    key=unit.key,
                    context=unit.context,
                    source_sha256=_sha(unit.source),
                    origin="memory",
                    match=match,
                    memory=name,
                    memory_sha256=sha,
                    tuids=tuids,
                )
            )
            break
    if direct is not None:
        findings.extend(direct.conflicts[before:])
    return prefills, provenance, findings


def _format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return {"pot": "po", "xlf": "xliff", "xml": "android"}.get(suffix, suffix)


def same_language(catalog_lang: str | None, wanted: str) -> bool:
    """True when ``wanted`` names the catalog's language: equal canonical tags, or
    the same tag without a region (``de`` for a ``de_DE`` catalog). A different
    script or variant (``sr`` vs ``sr-Latn``) is another language."""
    if not catalog_lang:
        return False
    have = canonical_locale(catalog_lang)
    if have == wanted:
        return True
    have_tag, want_tag = Language.get(have), Language.get(wanted)
    return want_tag.territory is None and (
        have_tag.language,
        have_tag.script,
        have_tag.variants,
    ) == (want_tag.language, want_tag.script, want_tag.variants)


def _plural_forms(template: Catalog, lang: str, plural_count: int | None):
    """Native positional keys required of every plural message ("0".."n-1")."""
    plural = [u for u in template.units if _eligible(u) and u.plural is not None]
    if not plural:
        return {}
    if template.origin_format == "ts":
        count = plural_count or qt_numerus.count(lang)
        return {str(i): "" for i in range(count)}
    shapes = {tuple(u.plural.forms) for u in plural}
    if len(shapes) != 1:
        raise ValueError("Plural messages disagree on their native forms")
    return dict.fromkeys(shapes.pop(), "")


def _keep(template: Catalog, plural_forms, qa: TextPolicy, keep_existing: bool):
    """Split a same-language catalog: kept prefills, untouched units, cleared units."""
    kept, untouched, findings, units = {}, set(), [], []
    required = tuple(plural_forms) or None
    for unit in template.units:
        values = {form: target for form, _, target in scalar_targets(unit)}
        filled = [bool(v and v.strip()) for v in values.values()]
        if not _eligible(unit) or not any(filled):
            units.append(unit)
            continue
        if not keep_existing:
            units.append(fill_unit(unit, {}, "untranslated"))
            continue
        units.append(unit)
        problems = (
            shape_findings(unit, required) + _blocking(unit, values, qa)
            if all(filled)
            else []
        )
        if all(filled) and not problems:
            state = "needs_review" if unit.state == "untranslated" else unit.state
            kept[unit.key] = Prefill(values=values, state=state, status="kept")
            continue
        untouched.add(unit.key)
        findings.append(
            Finding(
                rule_id="KEPT-INCOMPLETE" if not all(filled) else "KEPT-QA-FAIL",
                severity="major",
                message="Existing translation left unchanged: "
                + (
                    "some forms are empty"
                    if not all(filled)
                    else ", ".join(sorted({f.rule_id for f in problems}))
                ),
                unit_key=unit.key,
            )
        )
    return template.model_copy(update={"units": units}), kept, untouched, findings


def _origin_text(p: UnitProvenance) -> str | None:
    if p.origin == "memory":
        return f"memory:{p.memory}#{p.tuids[0]};match={p.match}"
    if p.origin == "engine" and p.reported_model:
        return f"engine:{p.reported_model};request={p.request_sha256}"
    return None


def write_origins(path: Path, origins: dict[int, str]) -> None:
    """Add or update ``<extra-localizzy-origin>`` in the given TS messages (by ordinal)."""
    raw = path.read_bytes()
    tree, ns = xml.parse(raw)
    elements = [message for _, message in xml.messages(tree.getroot(), ns)]
    encoding = tree.docinfo.encoding or "UTF-8"
    spans = ts_splice.message_spans(raw)
    ts_splice.check_spans(raw, spans, elements, encoding)
    style = ts_splice.detect_style(raw, encoding)
    replacements = {}
    for ordinal, text in sorted(origins.items()):
        message = elements[ordinal]
        node = message.find(ns + "extra-localizzy-origin")
        created = []
        if node is None:
            node = etree.SubElement(message, ns + "extra-localizzy-origin")
            created = [node]
        elif xml.text(node, ns) == text:
            continue
        xml.set_text(node, text, ns)
        replacements[ordinal] = ts_splice.render_message(
            message, style, spans[ordinal].indent, created
        )
    if replacements:
        raw = ts_splice.splice(raw, replacements)
        load_bytes(raw)
        atomic_write(path, raw)


def _template(loaded: Catalog, raw: bytes, fmt: str, wanted: str, plural_count):
    """The catalog to fill, and whether it is the input's own language."""
    if same_language(loaded.target_lang, wanted):
        return loaded, True
    if fmt != "ts":
        raise ValueError(
            f"Only TS catalogs can be prepared for a new language; "
            f"{fmt} catalog is {loaded.target_lang!r}, wanted {wanted!r}"
        )
    numerus = any(u.plural is not None and _eligible(u) for u in loaded.units)
    count = plural_count or (qt_numerus.count(wanted) if numerus else 2)
    return prepare_translation(raw, target_lang=wanted, plural_count=count), False


def translate_file(
    catalog: Path,
    *,
    target: str,
    out: Path,
    direct_memories: Sequence[Path] = (),
    glossary_memories: Sequence[Path] = (),
    memory_lang: str | None = None,
    glossary_statuses: frozenset[str] = DEFAULT_STATUSES,
    engine: EngineSpec | None = None,
    cache_path: Path | None = None,
    plural_count: int | None = None,
    keep_existing: bool = True,
    policy: MemoryPolicy = MemoryPolicy(),
    report: Path | None = None,
    provenance: Literal["sidecar", "extra"] = "sidecar",
    request: Request | None = None,
    style: str = "",
) -> TranslateReport:
    """Translate one catalog file into ``out`` and write the JSON report sidecar.

    Without ``engine`` no provider is called: units without a kept target or memory
    hit stay pending (``counts["pending"]``). ``request`` replaces the abersetz
    transport. ``cache_path`` defaults to ``.localizzy/translation-cache.sqlite``
    next to ``out``; ``report`` defaults to ``OUT.localizzy.json``.
    """
    catalog, out = Path(catalog), Path(out)
    if provenance not in ("sidecar", "extra"):
        raise ValueError("provenance must be 'sidecar' or 'extra'")
    raw = catalog.read_bytes()
    fmt = _format(catalog)
    loaded = load_any(catalog)
    wanted = canonical_locale(str(target))
    template, same = _template(loaded, raw, fmt, wanted, plural_count)
    if out.resolve() == catalog.resolve() and not same:
        raise ValueError("Output would overwrite the input with another language")
    lang = template.target_lang or wanted
    qa = TextPolicy()
    plural_forms = _plural_forms(template, wanted, plural_count)
    kept, untouched, findings = {}, set(), []
    if same:
        template, kept, untouched, findings = _keep(
            template, plural_forms, qa, keep_existing
        )
    load = {"source_lang": template.source_lang, "target_lang": lang}
    direct = (
        DirectMemory.load(list(direct_memories), memory_lang=memory_lang, **load)
        if direct_memories
        else None
    )
    glossary = (
        Glossary.load(
            list(glossary_memories),
            memory_lang=memory_lang,
            statuses=frozenset(glossary_statuses),
            **load,
        )
        if glossary_memories
        else None
    )
    work = template.model_copy(
        update={"units": [u for u in template.units if u.key not in untouched]}
    )
    lookup = work.model_copy(
        update={"units": [u for u in work.units if u.key not in kept]}
    )
    memory, memory_rows, memory_findings = memory_prefill(
        lookup, direct=direct, glossary=glossary, policy=policy, qa=qa
    )
    context = GlossaryContext(glossary, style=style)
    options = {
        "plural_forms": plural_forms,
        "context": context,
        "policy": qa,
        "prefilled": {**kept, **memory},
    }
    if engine is None:
        result = translate_catalog(work, None, **options)
    else:
        path = cache_path or out.parent / ".localizzy" / "translation-cache.sqlite"
        identity = f"{VALIDATION_IDENTITY}:{qa.model_dump_json()}"
        with open_cache(
            engine, path, validation_identity=identity, request=request
        ) as cache:
            result = translate_catalog(work, cache, **options)
    done = {u.key: u for u in result.catalog.units}
    final = template.model_copy(
        update={"units": [done.get(u.key, u) for u in template.units]}
    )
    if fmt == "ts":
        ts.dump(final, out)
    else:
        convert_catalog(final, fmt, out)
    rows = _provenance(template, result, memory_rows, untouched, context)
    if provenance == "extra" and fmt == "ts":
        origins = {
            int(unit.record_id.split(":")[1]): text
            for unit, row in zip(final.units, rows, strict=True)
            if unit.record_id and (text := _origin_text(row))
        }
        write_origins(out, origins)
    all_findings = memory_findings + findings + list(result.findings)
    counts = _counts(rows, all_findings)
    memories = []
    if direct is not None:
        memories.append({"role": "direct", **direct.summary()})
    if glossary is not None:
        memories.append({"role": "glossary", **glossary.summary()})
    summary = TranslateReport(
        catalog=str(catalog),
        catalog_sha256=hashlib.sha256(raw).hexdigest(),
        out=str(out),
        source_lang=template.source_lang,
        target_lang=lang,
        memories=memories,
        counts=counts,
        units=rows,
        findings=all_findings,
        ready=result.ready and not untouched,
    )
    atomic_write(
        Path(report) if report else Path(f"{out}.localizzy.json"),
        (
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2)
            + "\n"
        ).encode(),
    )
    return summary


def _provenance(template, result, memory_rows, untouched, context):
    """One UnitProvenance per template unit, in catalog order."""
    by_memory = {row.key: row for row in memory_rows}
    status = {d.key: d.status for d in result.dispositions}
    evidence = {i: p for p in result.providers for i in p.item_ids}
    rows = []
    for unit in template.units:
        base = {
            "key": unit.key,
            "context": unit.context,
            "source_sha256": _sha(unit.source),
        }
        state = status.get(unit.key)
        if unit.key in by_memory:
            rows.append(by_memory[unit.key])
        elif unit.key in untouched or state == "kept":
            rows.append(UnitProvenance(origin="kept", **base))
        elif state in ("excluded_empty", "excluded_vanished"):
            rows.append(UnitProvenance(origin="excluded", **base))
        else:
            ids = [item_id(unit, form) for form, _, _ in scalar_targets(unit)]
            terms = sorted({t for i in ids for t in context.used_terms.get(i, ())})
            proof = next((evidence[i] for i in ids if i in evidence), None)
            rows.append(
                UnitProvenance(
                    origin="pending" if state == "pending" else "engine",
                    glossary_terms=tuple(terms),
                    requested_model=proof.requested_model if proof else None,
                    reported_model=proof.reported_model if proof else None,
                    request_sha256=proof.request_sha256 if proof else None,
                    **base,
                )
            )
    return rows


def _counts(rows: list[UnitProvenance], findings: list[Finding]) -> dict[str, int]:
    counts = dict.fromkeys(
        (
            "kept",
            "memory_id",
            "memory_context",
            "memory_source",
            "memory_term",
            "engine",
            "pending",
            "excluded",
        ),
        0,
    )
    for row in rows:
        counts[f"memory_{row.match}" if row.origin == "memory" else row.origin] += 1
    counts["memory_rejected_qa"] = sum(
        f.rule_id == "MEMORY-QA-REJECT" for f in findings
    )
    counts["memory_conflict"] = sum(f.rule_id == "MEMORY-CONFLICT" for f in findings)
    return counts
