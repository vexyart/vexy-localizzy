# this_file: src/vexy_localizzy/fluent_resources.py
"""Bounded legacy Fluent projections using the published syntax parser/serializer."""

from collections.abc import Iterator

from fluent.syntax import FluentParser, ast, serializer

MAX_VARIANTS = 10_000


def flatten_pattern(
    pattern: ast.Pattern, *, max_variants: int = MAX_VARIANTS
) -> list[tuple[str, str]]:
    """Expand select branches in order; defaults omit suffixes, whitespace collapses.

    This is an extraction projection, not evaluation. Variables, functions and
    references remain Fluent expressions. Refuse Cartesian expansion beyond the
    per-pattern bound before allocating that expansion.
    """
    if type(max_variants) is not int or max_variants < 1:
        raise ValueError("Fluent variant limit must be a positive integer")
    combos: list[tuple[str, str]] = [("", "")]
    for element in pattern.elements:
        if isinstance(element, ast.TextElement):
            combos = [(suffix, text + element.value) for suffix, text in combos]
            continue
        expression = element.expression if isinstance(element, ast.Placeable) else None
        if isinstance(expression, ast.SelectExpression):
            expanded = []
            for variant in expression.variants:
                key = serializer.serialize_variant_key(variant.key)
                tag = "" if variant.default else f"[{key}]"
                branches = flatten_pattern(variant.value, max_variants=max_variants)
                if len(expanded) + len(branches) * len(combos) > max_variants:
                    raise ValueError("Fluent pattern exceeds variant limit")
                expanded.extend(
                    (suffix + tag + sub_suffix, text + sub_text)
                    for sub_suffix, sub_text in branches
                    for suffix, text in combos
                )
            combos = expanded
        else:
            piece = serializer.serialize_element(element)
            combos = [(suffix, text + piece) for suffix, text in combos]
    return [(suffix, " ".join(text.split())) for suffix, text in combos]


def parse_ftl(
    text: str, *, max_variants: int = MAX_VARIANTS
) -> Iterator[tuple[str, str]]:
    """Yield ordered term/message/attribute pairs, refusing syntax junk up front.

    Keep repeated IDs for the caller's duplicate policy. Each pattern is fully
    checked before yielding its variants. Keep the original resource for native
    editing; this historical projection omits comments and collapses whitespace.
    """
    if type(max_variants) is not int or max_variants < 1:
        raise ValueError("Fluent variant limit must be a positive integer")
    resource = FluentParser().parse(text)
    for entry in resource.body:
        if isinstance(entry, ast.Junk):
            raise ValueError(f"Invalid Fluent resource at offset {entry.span.start}")
    for entry in resource.body:
        if not isinstance(entry, ast.Message | ast.Term):
            continue
        name = ("-" if isinstance(entry, ast.Term) else "") + entry.id.name
        patterns = [(name, entry.value)] if entry.value else []
        patterns += [
            (f"{name}.{attr.id.name}", attr.value) for attr in entry.attributes
        ]
        for key, pattern in patterns:
            for suffix, value in flatten_pattern(pattern, max_variants=max_variants):
                yield key + suffix, value
