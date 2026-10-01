# this_file: tests/test_content_qa.py
"""Translation content contracts independent of model prompts and cached claims."""

import pytest

from vexy_localizzy.qa.text import TextPolicy, check_text, validate_batch
from vexy_localizzy.translate.types import (
    TranslationBatch,
    TranslationItem,
    TranslationResult,
)


def rules(source, target, **options):
    return {f.rule_id for f in check_text(source, target, policy=TextPolicy(**options))}


def test_blank_target_when_over_limit_then_reports_both_failures():
    assert rules("Open", "     ", max_length=3) == {"LEN-OVER", "TARGET-EMPTY"}


@pytest.mark.parametrize(
    "source,target",
    [
        ("%L1 %n %Ln %2", "%1 %n %Ln %2"),
        ("%1 %1", "%1"),
        ("%1", "%1 %2"),
        ("%n items", "%Ln elementów"),
    ],
)
def test_qt_when_arguments_change_then_critical_finding(source, target):
    findings = check_text(source, target)
    assert any(
        f.rule_id == "PH-MISMATCH" and f.severity == "critical" for f in findings
    )


def test_qt_when_arguments_reordered_then_no_placeholder_finding():
    assert not rules("%1 of %L2: %n", "%n: %L2 / %1")
    assert not rules("Done 50%", "Gotowe 50%")


@pytest.mark.parametrize(
    "source,target",
    [
        ("{name!r:>10} {count}", "{name!s:>10} {count}"),
        ("{value:{width}.{precision}f}", "{value:{width}.{precision}g}"),
        ("{name} {name}", "{name}"),
        ("{name}", "{name"),
        ("{} {}", "{}"),
    ],
)
def test_braces_when_format_changes_then_finding(source, target):
    assert rules(source, target, placeholder_styles=("python_brace",)) & {
        "PH-MISMATCH",
        "PH-SYNTAX",
    }


def test_braces_when_escaped_or_reordered_then_valid():
    assert not rules(
        "{{literal}} {a} {b}",
        "{{dosłownie}} {b} {a}",
        placeholder_styles=("python_brace",),
    )


@pytest.mark.parametrize(
    "source,target",
    [
        ("<b><i>Text</i></b>", "<b><i>Tekst</b></i>"),
        ("<b>Text</b>", "<i>Tekst</i>"),
        (
            '<a href="https://example.test/">Help</a>',
            '<a href="https://other.test/">Pomoc</a>',
        ),
        ("Plain text", "<b>Tekst</b>"),
        (
            '<span style="color:red">Text</span>',
            '<span style="color:blue">Tekst</span>',
        ),
        ("<b>Text</b>", "<b>Tekst"),
        (
            "<style>p { color:red }</style><p>Text</p>",
            "<style>p { color:blue }</style><p>Tekst</p>",
        ),
    ],
)
def test_markup_when_structure_or_protected_attributes_change_then_critical(
    source, target
):
    assert any(
        f.rule_id.startswith("TAG-") and f.severity == "critical"
        for f in check_text(source, target)
    )


def test_markup_when_equivalent_serialization_then_valid():
    assert not rules(
        '<b>Text</b><br><a href="x" title="Help">Help</a>',
        "<B>Tekst</B><br/><a title='Pomoc' href='x'>Pomoc</a>",
    )
    assert not rules("Value < 3", "Wartość < 3")


def test_markup_when_source_already_unbalanced_then_preserved_defect_is_visible():
    findings = check_text("<b>Text", "<b>Tekst")
    assert any(f.rule_id == "SOURCE-MARKUP" for f in findings)
    assert not any(f.severity == "critical" for f in findings)


@pytest.mark.parametrize(
    "source,target", [("&Open", "Otwórz"), ("R&&D", "R&D"), ("&Open", "& Otwórz")]
)
def test_mnemonic_when_dropped_added_or_invalid_then_finding(source, target):
    assert "ACCEL-MISMATCH" in rules(source, target)


def test_mnemonic_when_localized_letter_or_html_entity_then_valid():
    assert not rules("&Open", "&Otwórz")
    assert not rules(
        '<a href="x?a=1&b=2">A &amp; B</a>', '<a href="x?a=1&b=2">A &amp; C</a>'
    )


def test_target_when_empty_unchanged_or_too_long_then_explicit_finding():
    assert "TARGET-EMPTY" in rules("Open", " ")
    assert "TARGET-UNCHANGED" in rules("Open", "Open")
    assert "LEN-OVER" in rules("Open", "Otwórz", max_length=3)


def test_validation_when_batch_has_broken_content_then_reject_with_item_identity():
    batch = TranslationBatch(
        source_lang="en",
        target_lang="pl",
        items=[TranslationItem(id="m1", source="%L1 files")],
    )
    result = TranslationResult(
        targets={"m1": "%1 plików"}, requested_model="one", reported_model="one"
    )
    with pytest.raises(ValueError, match="m1.*PH-MISMATCH"):
        validate_batch(batch, result)


def test_policy_when_invalid_configuration_then_fail_before_content_checks():
    with pytest.raises(ValueError):
        TextPolicy(placeholder_styles=("guess",))
    with pytest.raises(ValueError):
        TextPolicy(max_length=-1)


def test_mnemonic_when_nested_in_markup_then_missing_marker_detected():
    assert "ACCEL-MISMATCH" in rules("<b>&Open</b>", "<b>Otwórz</b>")


def test_markup_when_script_added_to_plain_text_then_rejected():
    assert "TAG-MISMATCH" in rules("Text", "<script>alert(1)</script>Tekst")


def test_braces_when_anonymous_arguments_swap_formats_then_rejected():
    assert "PH-MISMATCH" in rules(
        "{} {:.2f}", "{:.2f} {}", placeholder_styles=("python_brace",)
    )


def test_braces_when_nested_anonymous_argument_moves_then_rejected():
    assert "PH-MISMATCH" in rules(
        "{v:{}} {}", "{} {v:{}}", placeholder_styles=("python_brace",)
    )


@pytest.mark.parametrize(
    "source,target", [("{[x]} {}", "{[x]} {0}"), ("{.real} {}", "{.real} {0}")]
)
def test_braces_when_automatic_root_has_suffix_then_manual_mixing_rejected(
    source, target
):
    assert "PH-SYNTAX" in rules(source, target, placeholder_styles=("python_brace",))


@pytest.mark.parametrize("source", ["<b>Open</b>", "<b>&copy;</b>", "<b>&#169;</b>"])
def test_markup_when_visible_content_removed_then_empty_finding(source):
    assert "TARGET-EMPTY" in rules(source, "<b>   </b>")


def _mismatch(source, target, **options):
    return [
        f for f in check_text(source, target, **options) if f.rule_id == "PH-MISMATCH"
    ]


@pytest.mark.parametrize(
    "source,target",
    [
        ("%n file(s)", "ملف واحد"),
        ("%Ln file(s)", "One file"),
        ("%n file(s) in %1", "One file in %1"),
    ],
)
def test_qt_when_count_optional_then_form_may_omit_the_count(source, target):
    assert _mismatch(source, target), "a form of several counts must keep the count"
    assert not _mismatch(source, target, count_optional=True), (
        "a one-count form may spell its number out"
    )


def test_qt_when_count_optional_and_count_kept_then_valid():
    assert not _mismatch("%n file(s)", "%n ملف", count_optional=True), (
        "keeping the count is always allowed"
    )


def test_qt_when_count_optional_then_every_other_placeholder_is_still_required():
    (finding,) = _mismatch("%n file(s) in %1", "One file", count_optional=True)
    assert finding.data["missing"] == ["%1"], "only the count may be omitted"
    (added,) = _mismatch("%n file(s)", "One file in %1", count_optional=True)
    assert added.data["extra"] == ["%1"], "an added argument is still an error"
    (swapped,) = _mismatch("%n file(s)", "%Ln files", count_optional=True)
    assert swapped.data["extra"] == ["%Ln"], "another count token is not an omission"
    assert _mismatch("%1 file(s)", "One file", count_optional=True), (
        "%1 is an argument, not the count"
    )


def test_qt_when_count_optional_and_target_empty_then_still_reported():
    findings = check_text("%n file(s)", " ", count_optional=True)
    assert [f.rule_id for f in findings] == ["TARGET-EMPTY"], findings


def _numerus_batch(lang, forms, source="%n file(s)", source_lang="en"):
    """A batch of one numerus message; ``forms`` maps form index to target."""
    items = [
        TranslationItem(id=f'["Files.n","{form}"]', source=source, form=form)
        for form in forms
    ]
    batch = TranslationBatch(source_lang=source_lang, target_lang=lang, items=items)
    targets = {item.id: forms[item.form] for item in items}
    result = TranslationResult(
        targets=targets, requested_model="one", reported_model="one"
    )
    return batch, result


ARABIC = {
    "0": "لا ملفات",
    "1": "ملف واحد",
    "2": "ملفان",
    "3": "%n ملفات",
    "4": "%n ملفًا",
    "5": "%n ملف",
}


def test_validation_when_arabic_one_count_forms_omit_the_count_then_accepted():
    assert validate_batch(*_numerus_batch("ar", ARABIC)) is None, (
        "the zero, one and two forms may spell their number out"
    )


@pytest.mark.parametrize("form", ["3", "4", "5"])
def test_validation_when_arabic_range_form_omits_the_count_then_rejected(form):
    forms = ARABIC | {form: "ملفات"}
    with pytest.raises(ValueError, match=rf'"{form}"\]: PH-MISMATCH'):
        validate_batch(*_numerus_batch("ar", forms))


@pytest.mark.parametrize(
    ("lang", "forms", "rejected"),
    [
        ("ru", {"0": "Один файл", "1": "%n файла", "2": "%n файлов"}, "0"),
        ("pl", {"0": "Jeden plik", "1": "pliki", "2": "%n plików"}, "1"),
        ("pl", {"0": "Jeden plik", "1": "%n pliki", "2": "plików"}, "2"),
        ("ja", {"0": "ファイル"}, "0"),
        ("fr", {"0": "Un fichier", "1": "%n fichiers"}, "0"),
        ("pt_BR", {"0": "Um arquivo", "1": "%n arquivos"}, "0"),
        ("tlh", {"0": "wa' teywI'", "1": "%n teywI'"}, "0"),
    ],
)
def test_validation_when_form_serves_several_counts_then_count_required(
    lang, forms, rejected
):
    with pytest.raises(ValueError, match=rf'"{rejected}"\]: PH-MISMATCH'):
        validate_batch(*_numerus_batch(lang, forms))


@pytest.mark.parametrize(
    ("lang", "forms"),
    [
        ("pl", {"0": "Jeden plik", "1": "%n pliki", "2": "%n plików"}),
        ("cs", {"0": "Jeden soubor", "1": "%n soubory", "2": "%n souborů"}),
        ("pt", {"0": "Um ficheiro", "1": "%n ficheiros"}),
    ],
)
def test_validation_when_singular_spelled_out_then_accepted(lang, forms):
    assert validate_batch(*_numerus_batch(lang, forms)) is None, lang


def test_validation_when_english_singular_spelled_out_then_accepted():
    batch, result = _numerus_batch(
        "en",
        {"0": "One file", "1": "%n files"},
        source="%n Datei(en)",
        source_lang="de",
    )
    assert validate_batch(batch, result) is None, "Qt practice: One file / %n files"
    batch, result = _numerus_batch(
        "en", {"0": "%n file", "1": "files"}, source="%n Datei(en)", source_lang="de"
    )
    with pytest.raises(ValueError, match=r'"1"\]: PH-MISMATCH'):
        validate_batch(batch, result)


@pytest.mark.parametrize(
    "item_id", ["m1", '["Files.n","scalar"]', '["Files.n"]', "[1]"]
)
def test_validation_when_item_is_not_a_numerus_form_then_count_required(item_id):
    batch = TranslationBatch(
        source_lang="en",
        target_lang="ar",
        items=[TranslationItem(id=item_id, source="%n file(s)")],
    )
    result = TranslationResult(
        targets={item_id: "ملف واحد"}, requested_model="one", reported_model="one"
    )
    with pytest.raises(ValueError, match="PH-MISMATCH"):
        validate_batch(batch, result)
