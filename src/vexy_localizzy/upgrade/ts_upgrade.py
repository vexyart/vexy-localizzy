# this_file: src/vexy_localizzy/upgrade/ts_upgrade.py
"""Upgrade an approved Qt catalog to a freshly extracted one.

FRESH (new lupdate output) supplies the messages the code now has. APPROVED
(the reviewed catalog) supplies translations. Every active FRESH message gets
exactly one category from ten tiers, applied as global passes so an early
message's fuzzy pairing can never take a later message's exact partner.
NEW is FRESH's bytes with only changed messages re-rendered; RETIRED holds the
APPROVED messages nobody ported.
"""

import copy
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

from vexy_localizzy.catalog import Record, Unit
from vexy_localizzy.formats import qt_numerus, ts_splice
from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.formats.ts_read import load_bytes
from vexy_localizzy.memory import DirectMemory, Glossary, MemoryHit
from vexy_localizzy.translate.cache import TranslationCache
from vexy_localizzy.translate.types import TranslationExample
from vexy_localizzy.upgrade import message_edit as edit
from vexy_localizzy.upgrade.engine_step import run_engine
from vexy_localizzy.upgrade.fuzzy import loose, similarity
from vexy_localizzy.upgrade.identity import (
    MessageRef,
    is_filled,
    key_identity,
    refs_from_tree,
)
from vexy_localizzy.upgrade.report import (
    FileInfo,
    MessageOutcome,
    UpgradeReport,
    count_outcomes,
    invariants,
)
from vexy_localizzy.upgrade.retired import build_retired


class UpgradeUsageError(ValueError):
    """Inputs cannot be upgraded as given (languages, paths)."""


class UpgradeInvariantError(RuntimeError):
    """The classification lost or duplicated a message; nothing was written."""


class UpgradeOptions(Record):
    finish_on: frozenset[str] = frozenset({"id", "context", "term"})
    fuzzy_threshold: float = 0.92
    fuzzy_margin: float = 0.02
    relocated_finished: bool = False
    no_engine: bool = False
    style: str = ""
    batch_size: int = 50
    glossary_limit: int = 60


@dataclass(frozen=True)
class UpgradeResult:
    new_bytes: bytes
    retired_bytes: bytes
    report: UpgradeReport


@dataclass
class Decision:
    """What NEW gets for one FRESH message; `action` picks the writer."""

    category: str
    action: str  # port | values | empty | untouched
    approved: MessageRef | None = None
    finished: bool | None = None
    old: bool = False
    kind: str = ""
    values: object = None
    extra: dict = field(default_factory=dict)


@dataclass
class _State:
    fresh: list[MessageRef]
    approved: list[MessageRef]
    units: list[Unit]
    counts: dict[int, int | None]
    options: UpgradeOptions
    decisions: dict[int, Decision] = field(default_factory=dict)
    consumed: set[int] = field(default_factory=set)
    reserved: set[int] = field(default_factory=set)
    no_fuzzy: set[int] = field(default_factory=set)
    paired: dict[int, MessageRef] = field(default_factory=dict)
    engine_extra: set[int] = field(default_factory=set)
    examples: dict[int, list[TranslationExample]] = field(default_factory=dict)
    hits: dict[int, MemoryHit | None] = field(default_factory=dict)
    ns: str = ""

    def remaining(self) -> list[MessageRef]:
        return [r for r in self.fresh if r.ordinal not in self.decisions]

    def taken(self, a: MessageRef) -> bool:
        return a.ordinal in self.consumed or a.ordinal in self.reserved

    def pool(self) -> list[MessageRef]:
        return [
            a for a in self.approved if a.active and a.has_text and not self.taken(a)
        ]

    def take(self, ref: MessageRef, cand: MessageRef) -> None:
        """Consume ``cand`` for ``ref``; reserve it instead when porting would
        drop reviewed plural forms, so RETIRED keeps the full message."""
        count = self.counts.get(ref.ordinal)
        if (
            ref.numerus
            and cand.has_text
            and count is not None
            and _forms(cand, self.ns) > count
        ):
            self.reserved.add(cand.ordinal)
        else:
            self.consumed.add(cand.ordinal)


def _forms(ref: MessageRef, ns: str) -> int:
    trans = xml.translation(ref.element, ns)
    return len(trans.findall(ns + "numerusform")) if trans is not None else 0


def _fresh_count(ref: MessageRef, ns: str, target: str) -> int | None:
    """The target's Qt numerus count; FRESH's own slot count only when Qt has no
    rule for the target (FRESH without a ``language`` attribute has 2 slots)."""
    if not ref.numerus:
        return None
    try:
        return qt_numerus.count(target)
    except qt_numerus.UnknownQtNumerus:
        return _forms(ref, ns) or None


def _example(approved: MessageRef, ns: str) -> TranslationExample | None:
    trans = xml.translation(approved.element, ns)
    if trans is None or not approved.has_text:
        return None
    node = trans.find(ns + "numerusform") if approved.numerus else trans
    if node is not None and node.get("variants") == "yes":
        node = node.find(ns + "lengthvariant")
    text = xml.text(node, ns) if node is not None else ""
    if not text.strip():
        return None
    return TranslationExample(
        source=approved.source,
        target=text,
        provenance=f"approved:{approved.context}|{approved.source}",
    )


def _pair_identities(st: _State, ns: str) -> None:
    """Tiers 1-3, plus id matches whose source changed (pinned fuzzy)."""
    by_id: dict[str, deque] = defaultdict(deque)
    by_key: dict[tuple, deque] = defaultdict(deque)
    all_ids = {a.msg_id for a in st.approved if a.msg_id}
    for a in st.approved:
        if a.kind in ("vanished", "obsolete"):
            continue
        if a.msg_id:
            by_id[a.msg_id].append(a)
        else:
            by_key[key_identity(a)].append(a)
    for ref in st.fresh:
        if ref.kind in ("vanished", "obsolete"):
            st.decisions[ref.ordinal] = Decision("excluded_vanished", "untouched")
            continue
        if ref.msg_id and ref.msg_id in all_ids:
            queue = by_id.get(ref.msg_id)
        else:
            queue = by_key.get(key_identity(ref))
        cand = queue.popleft() if queue else None
        if not ref.source:
            if cand is not None:
                st.consumed.add(cand.ordinal)
            st.decisions[ref.ordinal] = Decision(
                "excluded_empty", "untouched", approved=cand
            )
            continue
        if cand is None:
            continue
        _classify_pair(st, ref, cand, ns)


def _classify_pair(st: _State, ref: MessageRef, cand: MessageRef, ns: str) -> None:
    if cand.numerus != ref.numerus:
        st.reserved.add(cand.ordinal)
        st.engine_extra.add(ref.ordinal)
        if example := _example(cand, ns):
            st.examples[ref.ordinal] = [example]
        st.decisions[ref.ordinal] = Decision("shape_changed", "pending", approved=cand)
        return
    st.take(ref, cand)
    if not cand.has_text:
        st.no_fuzzy.add(ref.ordinal)
        st.paired[ref.ordinal] = cand
        return
    fresh_count = st.counts.get(ref.ordinal)
    if (cand.source, cand.comment) != (ref.source, ref.comment):
        same = loose(cand.source) == loose(ref.source)
        st.decisions[ref.ordinal] = Decision(
            "fuzzy_exact_loose" if same else "fuzzy_similar",
            "port",
            approved=cand,
            finished=False,
            old=True,
            extra={"similarity": round(similarity(cand.source, ref.source), 4)},
        )
        return
    if ref.numerus and fresh_count is not None and _forms(cand, ns) != fresh_count:
        st.decisions[ref.ordinal] = Decision(
            "plural_count_changed", "port", approved=cand, finished=False
        )
        return
    category = "exact_unfinished" if cand.kind == "unfinished" else "exact"
    st.decisions[ref.ordinal] = Decision(category, "port", approved=cand)


def _memory_hit(st: _State, ref: MessageRef, direct: DirectMemory) -> MemoryHit | None:
    if ref.ordinal not in st.hits:
        unit = st.units[ref.ordinal]
        count = st.counts.get(ref.ordinal)
        st.hits[ref.ordinal] = direct.lookup(unit, form_count=count)
    return st.hits[ref.ordinal]


def _memory_decision(st: _State, ref: MessageRef, hit: MemoryHit) -> Decision:
    if ref.numerus:
        kind, values = "forms", [hit.values[str(i)] for i in range(len(hit.values))]
    else:
        kind, values = "scalar", hit.values["scalar"]
    entries = hit.entries
    return Decision(
        f"memory_{hit.match}",
        "values",
        finished=hit.match in st.options.finish_on,
        kind=kind,
        values=values,
        extra={"memory": entries[0].memory, "tuids": [e.tuid for e in entries]},
    )


def _memory_pass(
    st: _State, direct: DirectMemory | None, classes: tuple[str, ...]
) -> None:
    if direct is None:
        return
    for ref in st.remaining():
        hit = _memory_hit(st, ref, direct)
        if hit is not None and hit.match in classes:
            st.decisions[ref.ordinal] = _memory_decision(st, ref, hit)


def _port_to(
    st: _State,
    ref: MessageRef,
    cand: MessageRef,
    category: str,
    finished: bool,
    old: bool,
    score: float | None = None,
) -> None:
    st.take(ref, cand)
    st.decisions[ref.ordinal] = Decision(
        category,
        "port",
        approved=cand,
        finished=finished,
        old=old,
        extra={"similarity": score} if score is not None else {},
    )


def _relocated_pass(st: _State) -> None:
    index: dict[tuple, list[MessageRef]] = defaultdict(list)
    for a in st.pool():
        index[(a.source, a.comment, a.numerus)].append(a)
    for ref in st.remaining():
        if ref.ordinal in st.no_fuzzy:
            continue
        found = [
            a
            for a in index.get((ref.source, ref.comment, ref.numerus), ())
            if a.context != ref.context and not st.taken(a)
        ]
        if len(found) == 1:
            # --relocated-finished keeps APPROVED's own state; it never promotes
            # an unfinished APPROVED translation to finished.
            finished = None if st.options.relocated_finished else False
            _port_to(st, ref, found[0], "relocated", finished, True)


def _loose_pass(st: _State) -> None:
    index: dict[tuple, list[MessageRef]] = defaultdict(list)
    for a in st.pool():
        index[(a.context, loose(a.source), a.numerus)].append(a)
    for ref in st.remaining():
        if ref.ordinal in st.no_fuzzy:
            continue
        found = [
            a
            for a in index.get((ref.context, loose(ref.source), ref.numerus), ())
            if not st.taken(a)
        ]
        if len(found) == 1:
            _port_to(st, ref, found[0], "fuzzy_exact_loose", False, True)


def _similar_pass(st: _State) -> None:
    index: dict[tuple, list[MessageRef]] = defaultdict(list)
    for a in st.pool():
        index[(a.context, a.numerus)].append(a)
    threshold, margin = st.options.fuzzy_threshold, st.options.fuzzy_margin
    for ref in st.remaining():
        if ref.ordinal in st.no_fuzzy:
            continue
        scored = sorted(
            (
                (similarity(a.source, ref.source), a)
                for a in index.get((ref.context, ref.numerus), ())
                if not st.taken(a)
            ),
            key=lambda pair: (-pair[0], pair[1].ordinal),
        )
        if not scored or scored[0][0] < threshold:
            continue
        if len(scored) > 1 and scored[0][0] - scored[1][0] < margin:
            continue
        score, best = scored[0]
        _port_to(st, ref, best, "fuzzy_similar", False, True, round(score, 4))


def _term_pass(
    st: _State, glossary: Glossary | None, direct: DirectMemory | None
) -> None:
    for ref in st.remaining():
        unit = st.units[ref.ordinal]
        term = None
        if glossary is not None and not ref.numerus and unit.variants is None:
            term = glossary.whole_match(ref.source)
        if term is not None:
            st.decisions[ref.ordinal] = Decision(
                "memory_term",
                "values",
                finished="term" in st.options.finish_on,
                kind="scalar",
                values=term.rendering,
                extra={
                    "memory": None,
                    "tuids": [term.tuid],
                    "glossary_terms": [term.source],
                },
            )
    _memory_pass(st, direct, ("source",))


def _engine_pass(
    st: _State,
    *,
    source_lang: str,
    target: str,
    cache: TranslationCache | None,
    glossary: Glossary | None,
) -> None:
    waiting = [r for r in st.remaining()] + [
        st.fresh[o] for o in sorted(st.engine_extra)
    ]
    use_engine = cache is not None and not st.options.no_engine
    fills = {}
    if use_engine and waiting:
        fills = run_engine(
            {r.ordinal: st.units[r.ordinal] for r in waiting},
            {r.ordinal: c for r in waiting if (c := st.counts.get(r.ordinal))},
            source_lang=source_lang,
            target_lang=target,
            cache=cache,
            glossary=glossary,
            examples=st.examples,
            style=st.options.style,
            batch_size=st.options.batch_size,
            glossary_limit=st.options.glossary_limit,
        )
    for ref in waiting:
        fill = fills.get(ref.ordinal)
        base = st.decisions.get(ref.ordinal)
        category = base.category if base is not None else None
        if fill is not None and fill.unit is not None:
            kind, values = _unit_values(fill.unit)
            extra = {"model": fill.model, "glossary_terms": list(fill.glossary_terms)}
            st.decisions[ref.ordinal] = Decision(
                category or "machine",
                "values",
                approved=base.approved if base else None,
                finished=False,
                kind=kind,
                values=values,
                extra=extra,
            )
            continue
        empty = category or ("pending" if use_engine else "untranslated")
        extra = {"glossary_terms": list(fill.glossary_terms)} if fill else {}
        st.decisions[ref.ordinal] = Decision(
            empty, "empty", approved=base.approved if base else None, extra=extra
        )


def _unit_values(unit: Unit) -> tuple[str, object]:
    if unit.plural is not None:
        return "forms", [
            unit.plural.forms[str(i)] for i in range(len(unit.plural.forms))
        ]
    if unit.variants is not None:
        return "variants", list(unit.variants)
    return "scalar", unit.target or ""


def _build(ref: MessageRef, decision: Decision, ns: str, count: int | None):
    """Return (new element, created nodes) for one decided FRESH message."""
    new = copy.deepcopy(ref.element)
    created: list = []
    if decision.action == "port":
        edit.port(
            new,
            decision.approved.element,
            ns,
            finished=decision.finished,
            form_count=count,
            old=decision.old,
            created=created,
        )
    elif decision.action == "values":
        edit.write_values(
            new,
            ns,
            decision.kind,
            decision.values,
            finished=bool(decision.finished),
            created=created,
        )
    elif decision.action == "empty":
        edit.write_empty(new, ns, count, created)
    return new, created


def _outcome(
    ref: MessageRef,
    decision: Decision,
    element,
    ns: str,
    paired: MessageRef | None = None,
) -> MessageOutcome:
    trans = xml.translation(element, ns)
    if decision.action == "untouched":
        state = "untouched"
    else:
        state = (
            "unfinished"
            if trans is None or trans.get("type") == "unfinished"
            else "finished"
        )
    approved = decision.approved or paired
    fuzzy = decision.category in ("relocated", "fuzzy_exact_loose", "fuzzy_similar")
    extra = decision.extra
    return MessageOutcome(
        fresh_ordinal=ref.ordinal,
        context=ref.context,
        source=ref.source,
        category=decision.category,
        state=state,
        filled=is_filled(trans, ns),
        approved_ordinal=approved.ordinal if approved is not None else None,
        approved_source=approved.source if approved is not None and fuzzy else None,
        similarity=extra.get("similarity"),
        memory=extra.get("memory"),
        tuids=extra.get("tuids", []),
        glossary_terms=extra.get("glossary_terms", []),
        model=extra.get("model"),
    )


def upgrade_ts(
    fresh: bytes,
    approved: bytes,
    *,
    target: str | None = None,
    direct: DirectMemory | None = None,
    glossary: Glossary | None = None,
    cache: TranslationCache | None = None,
    options: UpgradeOptions = UpgradeOptions(),
) -> UpgradeResult:
    """Classify every FRESH message, then splice NEW and build RETIRED in memory."""
    tree, ns = xml.parse(fresh)
    root = tree.getroot()
    a_tree, a_ns = xml.parse(approved)
    a_root = a_tree.getroot()
    if ns != a_ns:
        raise UpgradeUsageError("FRESH and APPROVED use different XML namespaces")
    source_lang = root.get("sourcelanguage") or "en"
    if source_lang != (a_root.get("sourcelanguage") or "en"):
        raise UpgradeUsageError(
            f"sourcelanguage differs: FRESH {source_lang!r}, APPROVED {a_root.get('sourcelanguage')!r}"
        )
    target_lang = (
        str(target) if target else a_root.get("language") or root.get("language")
    )
    if not target_lang:
        raise UpgradeUsageError("No target language: APPROVED has none; pass target")
    fresh_refs = refs_from_tree(root, ns)
    encoding = tree.docinfo.encoding or "UTF-8"
    spans = ts_splice.message_spans(fresh)
    ts_splice.check_spans(fresh, spans, [r.element for r in fresh_refs], encoding)
    st = _State(
        fresh=fresh_refs,
        approved=refs_from_tree(a_root, a_ns),
        units=load_bytes(fresh).units,
        counts={r.ordinal: _fresh_count(r, ns, target_lang) for r in fresh_refs},
        options=options,
        ns=ns,
    )
    _pair_identities(st, ns)
    _memory_pass(st, direct, ("id", "context"))
    _relocated_pass(st)
    _loose_pass(st)
    _similar_pass(st)
    _term_pass(st, glossary, direct)
    _engine_pass(
        st, source_lang=source_lang, target=target_lang, cache=cache, glossary=glossary
    )

    replacements: dict[int, bytes] = {}
    outcomes: list[MessageOutcome] = []
    style = None
    for ref in fresh_refs:
        decision = st.decisions[ref.ordinal]
        element = ref.element
        if decision.action != "untouched":
            new, created = _build(ref, decision, ns, st.counts.get(ref.ordinal))
            if edit.c14n(new) != edit.c14n(ref.element):
                ref.element.getparent().replace(ref.element, new)
                style = style or ts_splice.detect_style(fresh, encoding)
                span = spans[ref.ordinal]
                rendered = ts_splice.render_message(new, style, span.indent, created)
                if rendered != fresh[span.start : span.end]:
                    replacements[ref.ordinal] = rendered
                element = new
        paired = st.paired.get(ref.ordinal)
        outcomes.append(_outcome(ref, decision, element, ns, paired))
    root_attrs = (
        {"language": target_lang} if target_lang != root.get("language") else None
    )
    new_bytes = fresh
    if replacements or root_attrs:
        new_bytes = ts_splice.splice(fresh, replacements, root_attrs=root_attrs)
    if len(load_bytes(new_bytes).units) != len(fresh_refs):
        raise ValueError("NEW TS lost messages while splicing")

    retired = {a.ordinal for a in st.approved} - st.consumed
    retired_bytes = build_retired(approved, sorted(retired))
    obsolete = sum(
        1 for o in retired if st.approved[o].kind in ("vanished", "obsolete")
    )
    active = sum(1 for r in fresh_refs if r.active)
    memories = []
    if direct is not None:
        memories.append({"role": "direct", **direct.summary()})
    if glossary is not None:
        memories.append({"role": "glossary", **glossary.summary()})
    report = UpgradeReport(
        fresh=FileInfo.of(fresh, len(fresh_refs)),
        approved=FileInfo.of(approved, len(st.approved)),
        out=FileInfo.of(new_bytes, len(fresh_refs)),
        retired=FileInfo.of(retired_bytes, len(retired)),
        target_lang=target_lang,
        memories=memories,
        options=json.loads(options.model_dump_json())
        | {"engine": cache is not None and not options.no_engine},
        counts=count_outcomes(outcomes, len(retired) - obsolete, obsolete),
        messages=outcomes,
        retired_ordinals=sorted(retired),
        invariants=invariants(
            outcomes, len(fresh_refs), active, len(st.approved), st.consumed, retired
        ),
    )
    return UpgradeResult(new_bytes, retired_bytes, report)


def _same(a: Path, b: Path) -> bool:
    return a.resolve() == b.resolve()


def upgrade(
    fresh: Path,
    approved: Path,
    *,
    out: Path,
    retired: Path,
    report: Path | None = None,
    **kw,
) -> UpgradeReport:
    """Run ``upgrade_ts`` on files; write NEW, RETIRED and the report only if valid."""
    fresh, approved, out, retired = map(Path, (fresh, approved, out, retired))
    outputs = [out, retired] + ([Path(report)] if report is not None else [])
    for output in outputs:
        if _same(output, fresh) or _same(output, approved):
            raise UpgradeUsageError(f"Refusing to overwrite an input: {output}")
    if len({p.resolve() for p in outputs}) != len(outputs):
        raise UpgradeUsageError("out, retired and report must be different files")
    result = upgrade_ts(fresh.read_bytes(), approved.read_bytes(), **kw)
    rep = result.report
    rep = rep.model_copy(
        update={
            "fresh": rep.fresh.model_copy(update={"path": str(fresh)}),
            "approved": rep.approved.model_copy(update={"path": str(approved)}),
            "out": rep.out.model_copy(update={"path": str(out)}),
            "retired": rep.retired.model_copy(update={"path": str(retired)}),
        }
    )
    if not rep.ok:
        raise UpgradeInvariantError(f"Upgrade invariants failed: {rep.invariants}")
    atomic_write(out, result.new_bytes)
    atomic_write(retired, result.retired_bytes)
    if report is not None:
        atomic_write(Path(report), (rep.model_dump_json(indent=2) + "\n").encode())
    return rep
