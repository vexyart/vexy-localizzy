# this_file: tests/test_catalog_qa.py
"""Every native form is checked, regardless of a catalog's claimed state."""

import pytest

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.qa_catalog import check_catalog


def catalog(unit):
    return Catalog(source_lang="en", target_lang="pl", units=[unit])


def test_catalog_when_plural_and_variant_have_errors_then_all_locations_reported():
    unit = Unit(
        key="k",
        context="C",
        source="%n items",
        plural=PluralForms(
            indexing="index",
            forms={"0": "%n sztuka", "1": "sztuki", "2": "%n sztuk"},
            variants={"2": ["%n sztuk", "szt."]},
        ),
        state="untranslated",
    )
    findings = check_catalog(catalog(unit), required_plural_forms=("0", "1", "2"))
    bad = {f.data.get("form") for f in findings if f.rule_id == "PH-MISMATCH"}
    assert bad == {"1", "2:1"}, "Every form must be checked even in unfinished catalogs"


@pytest.mark.parametrize(
    "forms,rule",
    [
        ({"0": "%n element", "1": "%n elementy"}, "PLURAL-MISS"),
        (
            {
                "0": "%n element",
                "1": "%n elementy",
                "2": "%n elementów",
                "3": "%n extra",
            },
            "PLURAL-EXTRA",
        ),
        ({"0": "%n element", "1": "", "2": "%n elementów"}, "TARGET-EMPTY"),
    ],
)
def test_catalog_when_native_plural_shape_invalid_then_rejected(forms, rule):
    unit = Unit(
        key="k",
        context="C",
        source="%n items",
        plural=PluralForms(indexing="index", forms=forms),
    )
    assert rule in {
        f.rule_id
        for f in check_catalog(catalog(unit), required_plural_forms=("0", "1", "2"))
    }


def test_catalog_when_plural_rule_unknown_then_explicit_failure():
    unit = Unit(
        key="k",
        context="C",
        source="%n items",
        plural=PluralForms(indexing="index", forms={"0": "%n element"}),
    )
    assert any(f.rule_id == "PLURAL-RULE" for f in check_catalog(catalog(unit)))


def test_catalog_when_variant_alias_inconsistent_then_finding():
    unit = Unit(
        key="k",
        context="C",
        source="%1 items",
        target="%1 elementów",
        variants=["inne", "%1 el."],
    )
    assert any(f.rule_id == "VARIANT-SHAPE" for f in check_catalog(catalog(unit)))


def test_catalog_when_vanished_or_empty_source_then_excluded():
    cat = Catalog(
        source_lang="en",
        target_lang="pl",
        units=[
            Unit(key="a", context="C", source="%1", state="vanished"),
            Unit(key="b", context="C", source=" "),
        ],
    )
    assert check_catalog(cat) == []


def test_catalog_when_plural_source_differs_then_each_index_uses_its_source():
    unit = Unit(
        key="k",
        context="C",
        source="%1 item",
        source_plural="%2 items",
        plural=PluralForms(
            indexing="index", forms={"0": "%1 element", "1": "%2 elementy"}
        ),
    )
    assert not check_catalog(catalog(unit), required_plural_forms=("0", "1"))


def test_accelerators_when_literal_ampersand_before_space_then_not_a_marker():
    from vexy_localizzy.qa import TextPolicy, check_text
    from vexy_localizzy.qa_placeholders import accelerators

    assert accelerators("Guides & Anchors") == (0, 0), (
        "an ampersand before a space is literal text"
    )
    assert accelerators("&Guides") == (1, 0)
    assert accelerators("Guides &") == (0, 0), "a trailing ampersand is literal text"
    assert accelerators("Save &&as &%") == (0, 1), (
        "&& is literal, &% is an invalid marker"
    )
    findings = check_text(
        "Guides & Anchors", "Linie pomocnicze i kotwice", policy=TextPolicy()
    )
    assert not [f for f in findings if f.rule_id == "ACCEL-MISMATCH"], (
        "translating a literal & as a word is fine"
    )
