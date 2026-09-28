# this_file: tests/upgrade/test_upgrade_fuzzy.py
"""Loose comparison rules for the upgrade fuzzy tiers."""

import pytest

from vexy_localizzy.upgrade import loose, similarity


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Open...", "Open…"),
        ("Save:", "Save"),
        ("  Save   as  ", "save as"),
        ("&File", "File"),
        ("Copy %1 to %2", "Copy %L3 to %4"),
        ("Found %n items", "Found %Ln items"),
        ("Hello {name}", "Hello {user}"),
        ("Café", "Café"),
    ],
)
def test_loose_when_cosmetic_difference_then_equal(a, b):
    assert loose(a) == loose(b), f"{a!r} and {b!r} should compare loosely equal"


def test_loose_when_double_ampersand_then_literal_kept():
    assert loose("Save && Close") == "save & close"


def test_loose_when_words_differ_then_not_equal():
    assert loose("Open file") != loose("Open folder")


def test_similarity_when_one_letter_edit_then_high():
    assert similarity("Show kerning pairs panel", "Show kerning pair panel") >= 0.92
    assert similarity("Open", "Quit") < 0.5
