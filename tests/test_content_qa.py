# this_file: tests/test_content_qa.py
"""Translation content contracts independent of model prompts and cached claims."""

import pytest

from vexy_localizzy.qa.text import TextPolicy, check_text, validate_batch
from vexy_localizzy.translation_types import (
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
