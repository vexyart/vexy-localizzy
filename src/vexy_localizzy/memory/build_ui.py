# this_file: src/vexy_localizzy/memory/build_ui.py
"""Build a project (direct) memory from every finished message of a Qt .ts catalog.

One TU per finished message, or per numerus form. The English source is the
message source; the target is the reviewed translation. Source/target pairs reproduced exactly by a whole
glossary term are dropped. Reviewed contextual translations remain in the direct
memory even when their source is a whole term. Exclusion also requires that the
glossary tier can serve the message: numerus and length-variant messages, and
sources whose term rendering fails the accelerator or placeholder QA ("&Kerning",
"Kerning %1"), stay in the project memory. This is the memory ``translate`` and
``upgrade`` read as ``--direct-memory``. The output is tagged with the catalog's
language (or ``lang``); the glossary only decides the exclusions.
"""

from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path

from lxml import etree

from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.glossary import Glossary
from vexy_localizzy.memory.tmx_write import TMXRecord, write_records
from vexy_localizzy.qa.text import TextPolicy, check_text

SKIP_TYPES = frozenset({"unfinished", "vanished", "obsolete"})
BLOCKING = ("major", "critical")


def catalog_units(
    raw: bytes,
) -> Iterator[tuple[str, str, list[str], dict[str, str], str]]:
    """Yield (tuid base, source, forms, props, kind) for every finished non-empty
    message; kind is ``scalar``, ``numerus`` or ``variants``."""
    tree, ns = xml.parse(raw)
    for context, message in xml.messages(tree.getroot(), ns):
        source = xml.text(message.find(ns + "source"), ns)
        trans = xml.translation(message, ns)
        if not source or trans is None or trans.get("type") in SKIP_TYPES:
            continue
        numerus = message.get("numerus") == "yes"
        forms = (
            [xml.text(f, ns) for f in trans.findall(ns + "numerusform")]
            if numerus
            else [xml.text(trans, ns)]
        )
        if not any(form.strip() for form in forms):
            continue
        props = {"x-context": context}
        message_id = message.get("id") or ""
        if message_id:
            props["x-message-id"] = message_id
        comment = message.find(ns + "comment")
        if comment is not None and xml.text(comment, ns):
            props["x-comment"] = xml.text(comment, ns)
        kind = (
            "numerus"
            if numerus
            else "variants"
            if trans.get("variants") == "yes"
            else "scalar"
        )
        yield (message_id or f"{context}|{source}"), source, forms, props, kind


def served_by_term(
    exclude: Glossary, source: str, kind: str, target: str | None = None
) -> bool:
    """True when the glossary reproduces this reviewed scalar translation exactly.

    Missing targets cannot prove redundancy. Case, inflection and contextual
    wording are retained rather than folded into a general glossary lemma.
    """
    if kind != "scalar" or (term := exclude.whole_match(source)) is None:
        return False
    if target is None or target != term.rendering:
        return False
    findings = check_text(source, term.rendering, policy=TextPolicy())
    return not any(f.severity in BLOCKING for f in findings)


def build_ui_records(
    raw: bytes, *, source_lang: str, target_lang: str, exclude: Glossary | None
) -> tuple[Iterator[TMXRecord], dict[str, int]]:
    counts = {"kept": 0, "dropped_core_terms": 0}

    def records():
        for base, source, forms, props, kind in catalog_units(raw):
            if exclude is not None and served_by_term(exclude, source, kind, forms[0]):
                counts["dropped_core_terms"] += 1
                continue
            for index, text in enumerate(forms):
                unit_props = dict(props)
                tuid = base
                if kind == "numerus":
                    unit_props["x-numerus-form"] = str(index)
                    tuid = f"{base}:{index}"
                counts["kept"] += 1
                yield TMXRecord(
                    key=tuid,
                    segments=((source_lang, source), (target_lang, text)),
                    properties=tuple(unit_props.items()),
                )

    return records(), counts


def build_ui(
    catalog: Path,
    out: Path,
    *,
    lang: str | None = None,
    exclude_memories: Sequence[Path] = (),
    note: str | None = None,
) -> dict:
    """Write the project memory of ``catalog`` to ``out``; return the counts."""
    raw = Path(catalog).read_bytes()
    root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False))
    source_lang = canonical_locale(root.get("sourcelanguage") or "en")
    catalog_lang = root.get("language") or ""
    if not (lang or catalog_lang):
        raise ValueError("The catalog has no language; pass lang=")
    target_lang = canonical_locale(str(lang or catalog_lang))
    exclude = None
    if exclude_memories:
        exclude = Glossary.load(
            [Path(p) for p in exclude_memories],
            source_lang=source_lang,
            target_lang=target_lang,
            statuses=frozenset({"approved", "proposed", "do-not-translate"}),
        )
    records, counts = build_ui_records(
        raw, source_lang=source_lang, target_lang=target_lang, exclude=exclude
    )
    header_note = note or (
        f"Project memory built from {Path(catalog).name}: every finished message "
        f"with a reviewed {target_lang} translation. Exact glossary source/target pairs are excluded; contextual variants are retained."
    )
    write_records(
        Path(out),
        records,
        source_lang=source_lang,
        creation_tool="vexy-localizzy tm build-ui",
        creation_date=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        header_note=header_note,
        header_properties=(("x-memory-kind", "direct"),),
    )
    return {"output": str(out), "language": target_lang, **counts}
