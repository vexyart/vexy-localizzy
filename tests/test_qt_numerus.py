# this_file: tests/test_qt_numerus.py
"""Qt numerus counts come from Qt's table, not from CLDR."""

import pytest

from vexy_localizzy.formats.qt_numerus import (
    QT_NUMERUS_FORMS,
    UnknownQtNumerus,
    count,
    form_index,
    single_number_forms,
)


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


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("ar", {0: 0, 1: 1, 2: 2, 3: 3, 10: 3, 11: 4, 99: 4, 100: 5, 102: 5, 103: 3}),
        ("ru", {0: 2, 1: 0, 2: 1, 5: 2, 11: 2, 12: 2, 21: 0, 22: 1, 101: 0}),
        ("pl", {0: 2, 1: 0, 2: 1, 5: 2, 12: 2, 21: 2, 22: 1, 101: 2}),
        ("cs", {0: 2, 1: 0, 2: 1, 4: 1, 5: 2, 21: 2}),
        ("en", {0: 1, 1: 0, 2: 1, 21: 1}),
        ("fr", {0: 0, 1: 0, 2: 1}),
        ("pt", {0: 1, 1: 0, 2: 1}),
        ("pt_BR", {0: 0, 1: 0, 2: 1}),
        ("ja", {0: 0, 1: 0, 2: 0, 100: 0}),
        ("lv", {0: 2, 1: 0, 2: 1, 11: 1, 21: 0}),
        ("cy", {0: 0, 1: 1, 2: 2, 5: 2, 6: 3, 7: 4}),
    ],
)
def test_form_index_when_count_given_then_qt_form_selected(lang, expected):
    got = {n: form_index(lang, n) for n in expected}
    assert got == expected, f"{lang} numerus forms by count"


@pytest.mark.parametrize(
    ("lang", "single"),
    [
        ("ar", {0, 1, 2}),  # zero, one and two; the other forms cover ranges
        ("en", {0}),
        ("de_DE", {0}),
        ("pt", {0}),
        ("pt-BR", set()),  # n <= 1 selects the first form for 0 and 1
        ("fr", set()),
        ("ru", set()),  # the first form also serves 21, 31, 101
        ("uk", set()),
        ("pl", {0}),
        ("cs", {0}),
        ("ja", set()),  # one form serves every count
        ("lv", {2}),  # the last form is the zero form
        ("cy", {0, 1, 3}),
        ("ga", {0, 1}),
        ("sl", set()),
        ("sr@latin", set()),
    ],
)
def test_single_number_forms_when_language_known_then_one_count_forms(lang, single):
    assert single_number_forms(lang) == single, (
        f"{lang}: forms that exactly one count selects"
    )


def test_single_number_forms_when_language_unknown_then_raises():
    with pytest.raises(UnknownQtNumerus):
        single_number_forms("tlh")


def test_form_index_when_every_table_language_probed_then_rule_fits_its_count():
    for lang, forms in QT_NUMERUS_FORMS.items():
        reached = {form_index(lang, n) for n in range(300)}
        assert reached == set(range(forms)), (
            f"{lang}: the rule must reach exactly the {forms} forms of the count table"
        )
