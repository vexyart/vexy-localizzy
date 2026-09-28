# this_file: src/vexy_localizzy/formats/android_read.py
"""Project strings, plural forms and array entries from Android resource XML."""

from pathlib import Path

from lxml import etree

from vexy_localizzy.catalog import Catalog, PluralForms, Unit, detect_placeholders
from vexy_localizzy.formats.android_text import value
from vexy_localizzy.formats.document import SourceDocument
from vexy_localizzy.formats.xliff_xml import read_tree

QUANTITIES = {"zero", "one", "two", "few", "many", "other"}


def parse(raw: bytes) -> etree._ElementTree:
    tree = read_tree(raw)
    if tree.getroot().tag != "resources":
        raise ValueError("Expected Android resources root")
    return tree


def records(root: etree._Element):
    seen = set()
    for index, node in enumerate(root):
        kind = node.tag
        if kind not in ("string", "plurals", "string-array"):
            continue
        name = node.get("name")
        if not name or (kind, name) in seen:
            raise ValueError("Android resources require unique nonempty names per type")
        seen.add((kind, name))
        if kind == "string-array":
            for item_index, item in enumerate(node.findall("item")):
                yield f"android:{index}:{item_index}", f"{name}[{item_index}]", item
        else:
            yield f"android:{index}", name, node


def plural_items(node: etree._Element) -> dict[str, etree._Element]:
    result = {}
    for item in node.findall("item"):
        quantity = item.get("quantity")
        if quantity not in QUANTITIES or quantity in result:
            raise ValueError("Invalid or duplicate Android plural quantity")
        result[quantity] = item
    if not result:
        raise ValueError("Android plurals cannot be empty")
    return result


def project(raw: bytes, source_lang: str = "en") -> Catalog:
    tree = parse(raw)
    units, used = [], set()
    for record_id, key, node in records(tree.getroot()):
        plural = None
        if node.tag == "plurals":
            forms = {
                quantity: value(item) for quantity, item in plural_items(node).items()
            }
            plural = PluralForms(forms=forms)
            source = forms.get("other", next(iter(forms.values())))
        else:
            source = value(node)
        while key in used:
            key += "~" + record_id
        used.add(key)
        units.append(
            Unit(
                key=key,
                context="",
                source=source,
                plural=plural,
                record_id=record_id,
                placeholders=detect_placeholders(source),
            )
        )
    return Catalog(
        source_lang=source_lang,
        units=units,
        origin_format="android",
        document=SourceDocument.capture(raw, "android"),
    )


def load(path: str | Path, *, source_lang: str = "en") -> Catalog:
    """Android XML is monolingual; locale is supplied externally, defaulting to English."""
    return project(Path(path).read_bytes(), source_lang)
