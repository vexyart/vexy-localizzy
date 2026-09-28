# this_file: src/vexy_localizzy/formats/i18next_tree.py
"""Native JSON paths and byte spans; strict JSON validation precedes tree parsing."""

import json
from decimal import Decimal

import tree_sitter_json
from tree_sitter import Language, Node, Parser

from vexy_localizzy.json_values import invalid_constant, unique_object
from vexy_localizzy.json_values import path_key as path_key

QUANTITIES = {"zero", "one", "two", "few", "many", "other"}


def parse(raw: bytes) -> Node:
    data = json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=unique_object,
        parse_float=Decimal,
        parse_constant=invalid_constant,
    )
    if not isinstance(data, dict):
        raise ValueError("i18next resource root must be an object")
    root = Parser(Language(tree_sitter_json.language())).parse(raw).root_node
    if root.has_error or len(root.named_children) != 1:
        raise ValueError("Unsupported i18next JSON syntax")
    return root.named_children[0]


def text(node: Node) -> str:
    value = json.loads(node.text)
    value.encode("utf-8")
    return value


def records(node: Node, path: tuple = ()):
    if node.type == "string":
        yield path_key(path), path, node
    elif node.type == "array":
        for index, child in enumerate(node.named_children):
            yield from records(child, (*path, index))
    elif node.type == "object":
        children = {
            text(pair.child_by_field_name("key")): pair.child_by_field_name("value")
            for pair in node.named_children
        }
        groups = {
            key.removesuffix("_other")
            for key, child in children.items()
            if key.endswith("_other") and key != "_other" and child.type == "string"
        }
        emitted = set()
        for key, child in children.items():
            base, _, suffix = key.rpartition("_")
            if base in groups and suffix in QUANTITIES and child.type == "string":
                if base not in emitted:
                    forms = {
                        k.rsplit("_", 1)[1]: v
                        for k, v in children.items()
                        if k.rpartition("_")[0] == base
                        and k.rpartition("_")[2] in QUANTITIES
                        and v.type == "string"
                    }
                    name = path_key((*path, base))
                    yield (
                        ("plural:" + name if base in children else name),
                        (*path, base),
                        forms,
                    )
                    emitted.add(base)
            else:
                yield from records(child, (*path, key))
