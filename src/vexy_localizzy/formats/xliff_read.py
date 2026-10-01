# this_file: src/vexy_localizzy/formats/xliff_read.py
"""Project XLIFF 1.2 messages without losing their original document."""

from pathlib import Path

from lxml import etree

from vexy_localizzy.catalog import (
    Catalog,
    PluralForms,
    Unit,
    derive_key,
    detect_placeholders,
)
from vexy_localizzy.formats.document import SourceDocument
from vexy_localizzy.formats.xliff_xml import (
    PLURALS,
    content,
    context,
    forms,
    parse,
    records,
)


def state(node, ns):
    target = node.find(ns + "target")
    if target is None:
        return "untranslated"
    if node.get("approved") == "yes":
        return "approved"
    value = target.get("state", "")
    if value in ("final", "signed-off"):
        return "approved"
    if value.startswith("needs-review") or (
        value and value not in ("new", "needs-translation", "translated")
    ):
        return "needs_review"
    if value in ("new", "needs-translation") or not content(target):
        return "untranslated"
    return "translated"


def message(node: etree._Element, ns: str) -> tuple[str, str | None]:
    sources, targets = node.findall(ns + "source"), node.findall(ns + "target")
    if len(sources) != 1 or len(targets) > 1:
        raise ValueError("XLIFF message requires one source and at most one target")
    segmented = node.findall(ns + "seg-source")
    if len(segmented) > 1:
        raise ValueError("XLIFF message cannot have multiple segmented sources")
    return content(segmented[0] if segmented else sources[0]), content(
        targets[0]
    ) if targets else None


def unit(node: etree._Element, ns: str, index: int) -> Unit:
    # The x-fl10n-* names are what releases before 1.1 wrote; they still load.
    ctx = (
        context(node, "x-localizzy-context", ns)
        or context(node, "x-fl10n-context", ns)
        or ""
    )
    disambiguation = context(node, "x-localizzy-disambiguation", ns) or context(
        node, "x-fl10n-disambiguation", ns
    )
    plural = None
    source_plural = context(node, "x-localizzy-source-plural", ns)
    if node.get("restype") == PLURALS:
        children = forms(node, ns)
        texts = {key: message(child, ns) for key, child in children.items()}
        source = next(iter(texts.values()))[0]
        if any(pair[0] != source for pair in texts.values()):
            raise ValueError("Distinct XLIFF plural sources require explicit mapping")
        indexing = context(node, "x-localizzy-plural-indexing", ns)
        indexing = indexing or (
            "index" if all(key.isdecimal() for key in texts) else "cldr"
        )
        plural = PluralForms(
            indexing=indexing, forms={key: pair[1] or "" for key, pair in texts.items()}
        )
        states = [state(child, ns) for child in children.values()]
        status = min(
            states, key=["untranslated", "needs_review", "translated", "approved"].index
        )
        target = None
    else:
        source, target = message(node, ns)
        status = state(node, ns)
    return Unit(
        key=node.get("id") or derive_key(ctx, source, disambiguation),
        context=ctx,
        source=source,
        source_plural=source_plural,
        target=target,
        plural=plural,
        state=status,
        disambiguation=disambiguation,
        notes=["".join(note.itertext()) for note in node.findall(ns + "note")],
        placeholders=detect_placeholders(source),
        record_id=f"xliff:{index}",
    )


def project(raw: bytes) -> Catalog:
    tree, ns = parse(raw)
    units, keys = [], set()
    for index, node in enumerate(records(tree.getroot(), ns)):
        current = unit(node, ns, index)
        key = current.key
        while key in keys:
            key += f"~{index}"
        keys.add(key)
        units.append(current.model_copy(update={"key": key}))
    file = tree.getroot().find(ns + "file")
    return Catalog(
        source_lang=file.get("source-language") or "en",
        target_lang=file.get("target-language"),
        units=units,
        origin_format="xliff",
        document=SourceDocument.capture(raw, "xliff"),
    )


def load(path: str | Path) -> Catalog:
    return project(Path(path).read_bytes())
