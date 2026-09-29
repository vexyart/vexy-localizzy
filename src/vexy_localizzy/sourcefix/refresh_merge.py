# this_file: src/vexy_localizzy/sourcefix/refresh_merge.py
"""A copy-edit rebuild must not remove strings missing from a partial checkout."""

import copy
import re
from dataclasses import replace

from lxml import etree

from vexy_localizzy.formats import ts_splice, ts_xml
from vexy_localizzy.sourcefix.catalog import Catalog, active, key


def retain_baseline(fresh: Catalog, previous: Catalog) -> bytes:
    """Restore unextracted active entries; Qt extraction is not deletion authority."""
    by_key = {key(context, msg): msg for context, msg in fresh.records}
    contexts = {
        context.findtext("name"): context
        for context in fresh.tree.getroot().findall("context")
    }
    for context, message in previous.records:
        identity = key(context, message)
        if not active(message):
            continue
        if identity in fresh.index:
            updated = fresh.index[identity]
            for name in ("translation", "oldsource", "translatorcomment"):
                previous = message.find(name)
                if previous is None:
                    continue
                current = updated.find(name)
                copied = copy.deepcopy(previous)
                if current is not None:
                    copied.tail = current.tail
                    updated.replace(current, copied)
                elif name == "oldsource":
                    updated.insert(updated.index(updated.find("source")) + 1, copied)
                else:
                    updated.append(copied)
            continue
        old = by_key.get(identity)
        copied = copy.deepcopy(message)
        if old is not None:
            copied.tail = old.tail
            old.getparent().replace(old, copied)
            continue
        if context not in contexts:
            parent = etree.SubElement(fresh.tree.getroot(), "context")
            etree.SubElement(parent, "name").text = context
            contexts[context] = parent
        contexts[context].append(copied)
    return etree.tostring(
        fresh.tree, encoding="utf-8", xml_declaration=True, pretty_print=True
    )


def _texts(node):
    children = [
        child for child in node if child.tag in {"numerusform", "lengthvariant"}
    ]
    if children:
        return [(child.tag, _texts(child)) for child in children]
    return ts_xml.text(node, "")


def verify_translations(previous: Catalog, fresh: Catalog) -> None:
    """Native refresh must preserve every existing translation, including plurals."""
    for identity, message in previous.index.items():
        updated = fresh.index.get(identity)
        if updated is None:
            raise ValueError(f"Rebuild lost an existing message: {identity}")
        old_target, new_target = (
            message.find("translation"),
            updated.find("translation"),
        )
        if old_target is None:
            continue
        if (
            new_target is None
            or _texts(old_target) != _texts(new_target)
            or old_target.get("type") != new_target.get("type")
        ):
            raise ValueError(f"Rebuild changed an existing translation: {identity}")


def protect_line_spaces(catalog: Catalog) -> bytes:
    """Keep significant text spaces as XML entities, avoiding trailing-space diffs."""
    style = replace(catalog.style, escape_eol_space=True)
    replacements = {}
    for i, (_, message) in enumerate(catalog.records):
        span = catalog.spans[i]
        if re.search(rb" +(?=\r?\n)", catalog.raw[span.start : span.end]):
            replacements[i] = ts_splice.render_message(message, style, span.indent)
    return ts_splice.splice(catalog.raw, replacements)
