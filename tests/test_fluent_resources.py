# this_file: tests/test_fluent_resources.py
"""Fluent extraction retains legacy ordering while rejecting incomplete input."""

import pytest
from fluent.syntax import FluentParser, ast

from vexy_localizzy.fluent_resources import flatten_pattern, parse_ftl

TEXT = """# Comment
-brand = Example
    .case = Brand
hello = Hello { $name }
    .title = More   words
items = { $n ->
    [one] One { -brand }
   *[other] Many { NUMBER($n) }
}
"""


def test_parse_when_messages_terms_attributes_and_selectors_then_exact_pairs():
    assert list(parse_ftl(TEXT)) == [
        ("-brand", "Example"),
        ("-brand.case", "Brand"),
        ("hello", "Hello { $name }"),
        ("hello.title", "More words"),
        ("items[one]", "One { -brand }"),
        ("items", "Many { NUMBER($n) }"),
    ]
    assert list(parse_ftl("## Only comments\n")) == []
    assert list(parse_ftl("")) == []


def test_parse_when_repeated_ids_then_preserve_order_for_callers():
    assert list(parse_ftl("same = First\nsame = Second\n")) == [
        ("same", "First"),
        ("same", "Second"),
    ]


def test_parse_when_numeric_selector_and_suffix_text_then_keep_all_variants():
    text = """count = Before { $n ->
    [0] zero
   *[other] many
} after
"""
    assert list(parse_ftl(text)) == [
        ("count[0]", "Before zero after"),
        ("count", "Before many after"),
    ]


def test_parse_when_nested_selectors_then_keep_ordered_suffixes():
    text = """nested = { $a ->
    [one] { $b ->
        [one] First
       *[other] Second
    }
   *[other] Third
}
"""
    assert list(parse_ftl(text)) == [
        ("nested[one][one]", "First"),
        ("nested[one]", "Second"),
        ("nested", "Third"),
    ]


@pytest.mark.parametrize(
    "text",
    ["good = Fine\nbroken = {\n", "not an entry", "select = { $n ->\n [one] One\n}\n"],
)
def test_parse_when_junk_present_then_fail_before_first_pair(text):
    pairs = parse_ftl(text)
    with pytest.raises(ValueError, match="Invalid Fluent"):
        next(pairs)


def test_flatten_when_cartesian_limit_exceeded_then_refuse_before_large_expansion():
    select = ast.Placeable(
        ast.SelectExpression(
            ast.VariableReference(ast.Identifier("n")),
            [
                ast.Variant(
                    ast.Identifier("one"), ast.Pattern([ast.TextElement("One")])
                ),
                ast.Variant(
                    ast.Identifier("other"),
                    ast.Pattern([ast.TextElement("Other")]),
                    default=True,
                ),
            ],
        )
    )
    pattern = ast.Pattern([select] * 30)
    with pytest.raises(ValueError, match="variant limit"):
        flatten_pattern(pattern, max_variants=4)
    assert flatten_pattern(ast.Pattern([select]), max_variants=2) == [
        ("[one]", "One"),
        ("", "Other"),
    ]


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, None])
def test_parse_when_variant_limit_invalid_then_fail(limit):
    with pytest.raises(ValueError, match="positive integer"):
        list(parse_ftl(TEXT, max_variants=limit))


def test_flatten_when_empty_pattern_then_preserve_legacy_empty_value():
    assert flatten_pattern(ast.Pattern([])) == [("", "")]


def test_parse_when_limit_applies_to_each_pattern_then_no_partial_pattern():
    pattern = FluentParser().parse(TEXT).body[-1].value
    with pytest.raises(ValueError, match="variant limit"):
        flatten_pattern(pattern, max_variants=1)
