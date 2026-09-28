# this_file: tests/test_qt_numerus.py
"""Qt numerus counts come from Qt's table, not from CLDR."""

import pytest

from vexy_localizzy.formats.qt_numerus import UnknownQtNumerus, count


@pytest.mark.parametrize(
    ("lang", "forms"),
    [
        ("en", 2),
        ("de_DE", 2),
        ("fr", 2),  # CLDR has three categories; Qt has two
        ("es_MX", 2),
        ("pl", 3),  # CLDR has four categories; Qt has three
        ("ru", 3),
        ("cs", 3),
        ("ja", 1),
        ("zh-Hans", 1),
        ("ar", 6),
        ("cy", 5),
        ("sl", 4),
        ("pt-BR", 2),
    ],
)
def test_count_when_language_known_then_matches_qt_table(lang, forms):
    assert count(lang) == forms, f"{lang} should have {forms} Qt numerus forms"


def test_count_when_language_unknown_then_raises():
    with pytest.raises(UnknownQtNumerus):
        count("tlh")


@pytest.mark.parametrize(
    ("lang", "forms"),
    [("no", 2), ("no_NO", 2), ("sr@latin", 3), ("sr_RS@latin", 3), ("ca@valencia", 2)],
)
def test_count_when_norwegian_or_qt_modifier_then_known(lang, forms):
    assert count(lang) == forms, f"{lang} should have {forms} Qt numerus forms"
