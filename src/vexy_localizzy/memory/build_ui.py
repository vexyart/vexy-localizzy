# this_file: src/vexy_localizzy/memory/build_ui.py
"""Build a project (direct) memory from every finished message of a Qt .ts catalog.

One TU per finished message, or per numerus form. The English source is the
message source; the target is the reviewed translation. Sources that are whole
glossary terms of an exclusion memory are dropped, so the project memory and the
core memory never hold the same string. This is the memory ``translate`` and
``upgrade`` read as ``--direct-memory``.
"""

from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path

from lxml import etree

from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.glossary import Glossary, match_text
from vexy_localizzy.memory.langmatch import select_language
from vexy_localizzy.tmx_writer import TMXRecord, write_records

SKIP_TYPES = frozenset({"unfinished", "vanished", "obsolete"})


def catalog_units(raw: bytes) -> Iterator[tuple[str, str, list[str], dict[str, str]]]:
    """Yield (tuid base, source, forms, props) for every finished non-empty message."""
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
        yield (message_id or f"{context}|{source}"), source, forms, props


def build_ui_records(
    raw: bytes, *, source_lang: str, target_lang: str, exclude: Glossary | None
) -> tuple[Iterator[TMXRecord], dict[str, int]]:
    owned = (
        {match_text(term.source).strip() for term in exclude.terms}
        if exclude
        else set()
    )
    counts = {"kept": 0, "dropped_core_terms": 0}

    def records():
        for base, source, forms, props in catalog_units(raw):
            if match_text(source).strip() in owned:
                counts["dropped_core_terms"] += 1
                continue
            for index, text in enumerate(forms):
                unit_props = dict(props)
                tuid = base
                if len(forms) > 1 or "x-numerus-form" in props:
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
    exclude = None
    if exclude_memories:
        exclude = Glossary.load(
            [Path(p) for p in exclude_memories],
            source_lang=source_lang,
            target_lang=catalog_lang or (lang or ""),
            memory_lang=lang,
            statuses=frozenset({"approved", "proposed", "do-not-translate"}),
        )
        target_lang = exclude.files[0].target_lang
    elif lang:
        target_lang = canonical_locale(str(lang))
    elif catalog_lang:
        target_lang = select_language([canonical_locale(catalog_lang)], catalog_lang)
    else:
        raise ValueError("The catalog has no language; pass lang=")
    records, counts = build_ui_records(
        raw, source_lang=source_lang, target_lang=target_lang, exclude=exclude
    )
    header_note = note or (
        f"Project memory built from {Path(catalog).name}: every finished message "
        f"with a reviewed {target_lang} translation. Glossary terms are excluded."
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
