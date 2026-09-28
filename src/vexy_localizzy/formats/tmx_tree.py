# this_file: src/vexy_localizzy/formats/tmx_tree.py
"""TMX document structure and explicit language projections."""

import json

from lxml import etree

from vexy_localizzy.formats.xliff_xml import read_tree
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.tmx import XML_LANG

METADATA = "x-localizzy-catalog-v1"
PROJECTION = "x-localizzy-projection-v1"


def parse(raw: bytes):
    tree = read_tree(raw)
    root = tree.getroot()
    name = etree.QName(root)
    if name.localname != "tmx":
        raise ValueError("Expected TMX root")
    ns = f"{{{name.namespace}}}" if name.namespace else ""
    if len(root.findall(ns + "header")) != 1 or len(root.findall(ns + "body")) != 1:
        raise ValueError("TMX requires exactly one header and body")
    return tree, ns


def variants(tu, ns):
    result = {}
    for tuv in tu.findall(ns + "tuv"):
        label = tuv.get(XML_LANG) or tuv.get("lang")
        if not label or len(tuv.findall(ns + "seg")) != 1:
            raise ValueError("TMX variant requires language and exactly one segment")
        result.setdefault(canonical_locale(label), []).append(tuv)
    if not result:
        raise ValueError("TMX unit has no language variants")
    return result


def selected(values, language, *, required=False):
    candidates = values.get(language, [])
    if len(candidates) > 1:
        raise ValueError(f"Ambiguous TMX variants for {language}")
    if not candidates and required:
        raise ValueError(f"TMX unit lacks selected source language {language}")
    return candidates[0] if candidates else None


def languages(tree, ns, source_lang=None, target_lang=None):
    root = tree.getroot()
    units = root.find(ns + "body").findall(ns + "tu")
    declared = root.find(ns + "header").get("srclang", "")
    if source_lang is None:
        sources = {tu.get("srclang", declared) for tu in units} or {declared}
        if any(not label or label.lower() == "*all*" for label in sources):
            raise ValueError("Supply an explicit TMX source language")
        sources = {canonical_locale(label) for label in sources}
        if len(sources) != 1:
            raise ValueError("Mixed TMX sources require an explicit source language")
        source_lang = sources.pop()
    source_lang = canonical_locale(source_lang)
    hints = [
        node
        for node in root.find(ns + "header").findall(ns + "prop")
        if node.get("type") == PROJECTION
    ]
    if len(hints) > 1:
        raise ValueError("Duplicate TMX projection metadata")
    if hints:
        pair = json.loads(hints[0].text or "")
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or not isinstance(pair[0], str)
            or (pair[1] is not None and not isinstance(pair[1], str))
        ):
            raise ValueError("Invalid TMX projection metadata")
        if target_lang is None and canonical_locale(pair[0]) == source_lang:
            target_lang = pair[1]
    others = set()
    for unit in units:
        values = variants(unit, ns)
        selected(values, source_lang, required=True)
        others.update(set(values) - {source_lang})
    if target_lang is None and len(others) == 1:
        target_lang = others.pop()
    if target_lang is not None:
        target_lang = canonical_locale(target_lang)
        if target_lang == source_lang:
            raise ValueError("TMX source and target projections must differ")
    return source_lang, target_lang


def metadata_node(tu, ns):
    nodes = [node for node in tu.findall(ns + "prop") if node.get("type") == METADATA]
    if len(nodes) > 1:
        raise ValueError("Duplicate Localizzy TMX metadata")
    return nodes[0] if nodes else None


def projection_key(source_lang, target_lang):
    return json.dumps([source_lang, target_lang], separators=(",", ":"))


def metadata_projections(tu, ns):
    node = metadata_node(tu, ns)
    if node is None:
        return {}
    payload = json.loads(node.text or "")
    if (
        not isinstance(payload, dict)
        or set(payload) != {"version", "projections"}
        or type(payload["version"]) is not int
        or payload["version"] != 1
        or not isinstance(payload["projections"], dict)
    ):
        raise ValueError("Unsupported Localizzy TMX metadata")
    return payload["projections"]
