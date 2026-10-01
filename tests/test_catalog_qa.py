# this_file: tests/test_catalog_qa.py
"""Every native form is checked, regardless of a catalog's claimed state."""

import pytest

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.qa.catalog import check_catalog


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
    from vexy_localizzy.qa.placeholders import accelerators

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


def _count_missing(lang, forms, source="%n file(s)", indexing="index", **plural):
    """Form keys with a PH-MISMATCH finding for one numerus message in ``lang``."""
    unit = Unit(
        key="k",
        context="C",
        source=source,
        plural=PluralForms(indexing=indexing, forms=forms, **plural),
    )
    cat = Catalog(source_lang="en", target_lang=lang, units=[unit])
    findings = check_catalog(cat, required_plural_forms=tuple(forms))
    return {f.data["form"] for f in findings if f.rule_id == "PH-MISMATCH"}


ARABIC = {
    "0": "لا ملفات",
    "1": "ملف واحد",
    "2": "ملفان",
    "3": "%n ملفات",
    "4": "%n ملفًا",
    "5": "%n ملف",
}


def test_catalog_when_arabic_zero_one_two_omit_the_count_then_clean():
    assert _count_missing("ar", ARABIC) == set(), (
        "forms that one count selects may spell the number out"
    )
    assert _count_missing("ar_EG", ARABIC) == set(), "a region keeps the rule"


def test_catalog_when_arabic_range_forms_omit_the_count_then_each_reported():
    forms = ARABIC | {"3": "ملفات", "4": "ملفًا", "5": "ملف"}
    assert _count_missing("ar", forms) == {"3", "4", "5"}, (
        "a form that covers several counts must keep the count"
    )


@pytest.mark.parametrize(
    ("lang", "forms", "reported"),
    [
        ("ru", {"0": "Один файл", "1": "%n файла", "2": "%n файлов"}, {"0"}),
        ("ru", {"0": "%n файл", "1": "файла", "2": "файлов"}, {"1", "2"}),
        ("pl", {"0": "Jeden plik", "1": "%n pliki", "2": "%n plików"}, set()),
        ("pl", {"0": "Jeden plik", "1": "pliki", "2": "plików"}, {"1", "2"}),
        ("en_GB", {"0": "One file", "1": "%n files"}, set()),
        ("en_GB", {"0": "%n file", "1": "files"}, {"1"}),
        ("ja", {"0": "ファイル"}, {"0"}),
        ("fr", {"0": "Un fichier", "1": "%n fichiers"}, {"0"}),
        ("pt_BR", {"0": "Um arquivo", "1": "%n arquivos"}, {"0"}),
        ("pt", {"0": "Um ficheiro", "1": "%n ficheiros"}, set()),
        ("tlh", {"0": "wa' teywI'", "1": "%n teywI'"}, {"0"}),
    ],
)
def test_catalog_when_form_omits_the_count_then_only_one_count_forms_pass(
    lang, forms, reported
):
    assert _count_missing(lang, forms) == reported, lang


def test_catalog_when_form_count_is_not_qts_then_count_required():
    assert _count_missing("ar", {"0": "ملف واحد", "1": "%n ملفات"}) == {"0"}, (
        "two forms are not Arabic's six, so Qt's rule does not apply"
    )


def test_catalog_when_forms_are_categories_then_count_required():
    forms = {"one": "One file", "other": "%n files"}
    assert _count_missing("en_GB", forms, indexing="cldr") == {"one"}, (
        "category-keyed plurals are not Qt numerus forms"
    )


def test_catalog_when_one_count_form_drops_another_argument_then_reported():
    forms = ARABIC | {"1": "ملف واحد"}
    with_folder = {key: f"{text} في %1" for key, text in forms.items()}
    assert _count_missing("ar", with_folder, source="%n file(s) in %1") == set()
    assert _count_missing("ar", forms, source="%n file(s) in %1") == set(forms), (
        "%1 is required in every form; only the count may be left out"
    )


def test_catalog_when_one_count_form_has_length_variants_then_each_may_omit():
    forms = {"0": "Jeden plik", "1": "%n pliki", "2": "%n plików"}
    variants = {"0": ["Jeden plik", "1 plik"], "2": ["%n plików", "pl."]}
    assert _count_missing("pl", forms, variants=variants) == {"2:1"}, (
        "variants of the singular may omit the count, variants of a range may not"
    )


def test_catalog_when_scalar_message_omits_the_count_then_reported():
    unit = Unit(key="k", context="C", source="%n file(s)", target="ملف واحد")
    cat = Catalog(source_lang="en", target_lang="ar", units=[unit])
    assert [f.rule_id for f in check_catalog(cat)] == ["PH-MISMATCH"], (
        "only numerus forms get the exemption"
    )
