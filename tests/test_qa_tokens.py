# this_file: tests/test_qa_tokens.py
"""Literal compatibility contracts preserve multiplicity and exact diagnostics."""

import pytest

from vexy_localizzy.qa_tokens import check_tokens


@pytest.mark.parametrize(
    "token,style",
    [
        ("%1", "qt"),
        ("%n", "qt"),
        ("%Ln", "qt"),
        ("%L1", "qt"),
        ("%s", "printf"),
        ("{name}", "python_brace"),
        ("{{count}}", "i18next"),
        ("{n, number}", "icu"),
        ("<b>", "html"),
    ],
)
def test_tokens_when_one_repeated_occurrence_lost_then_report_missing(token, style):
    findings = check_tokens(token + token, token, styles=(style,), unit_key="sample")
    assert len(findings) == 1 and findings[0].unit_key == "sample"
    assert findings[0].rule_id == ("TAG-MISS" if style == "html" else "PH-MISS")
    assert findings[0].data.get("tag", findings[0].data.get("token")) == token


def test_tokens_when_reordered_then_no_findings():
    assert check_tokens("%1 {name} %1", "{name} %1 %1") == []


def test_tokens_when_target_absent_then_legacy_skip_and_empty_target_checked():
    assert check_tokens("%1", None) == []
    assert check_tokens("%1", "")[0].rule_id == "PH-MISS"


def test_tokens_when_extra_then_legacy_message_and_data():
    finding = check_tokens("Open", "Open %1", styles=("qt",), unit_key="key")[0]
    assert finding.message == "Unexpected placeholder '%1' in target."
    assert finding.data == {"token": "%1", "style": "qt"}


def test_tokens_when_unknown_style_then_explicit_failure():
    with pytest.raises(ValueError, match="style"):
        check_tokens("a", "b", styles=("unknown",))
