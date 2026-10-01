# this_file: tests/test_plurals_report.py
"""Plural tables, the findings renderers, tool discovery and the doctor report."""

import json

import pytest

from vexy_localizzy import doctor, external, plurals, report
from vexy_localizzy.catalog import Finding


def test_required_categories_when_known_and_unknown_language():
    assert plurals.required_categories("pl_PL") == {"one", "few", "many", "other"}
    assert plurals.required_categories("xx") == {"other"}, "unknown falls back to other"
    assert plurals.required_categories(None) == {"other"}


def test_plural_forms_header_when_french_then_two_forms_n_gt_1():
    assert plurals.plural_forms_header("fr") == "nplurals=2; plural=(n > 1);"
    assert plurals.plural_forms_header("ru").startswith("nplurals=3;")
    assert plurals.plural_forms_header("nl") == "nplurals=2; plural=(n != 1);", (
        "a two-form language outside the table gets the common rule"
    )
    assert plurals.plural_forms_header("vi") == "nplurals=1; plural=0;"
    with pytest.raises(ValueError, match="plural rule"):
        plurals.plural_forms_header("uk")


def test_positional_categories_when_unknown_then_value_error():
    assert plurals.positional_categories("pl") == ("one", "few", "many")
    assert plurals.positional_categories("de-AT") == ("one", "other")
    with pytest.raises(ValueError, match="plural_order"):
        plurals.positional_categories("ga")


def test_parse_icu_plural_when_block_mid_string_then_arms_read():
    parsed = plurals.parse_icu_plural(
        "You have {n, plural, =0 {none} one {# x} other {# xs}}."
    )
    assert parsed.forms == {"zero": "none", "one": "# x", "other": "# xs"}, parsed.forms
    assert plurals.parse_icu_plural("plain {name}") is None
    assert plurals.parse_icu_plural("{n, plural, one {x}") is None, "unbalanced block"


def _findings():
    return [
        Finding(
            rule_id="QT-TR-002", severity="critical", message="m", location="a.cpp:10:5"
        ),
        Finding(rule_id="CUSTOM", severity="minor", message="n", unit_key="k"),
        Finding(
            rule_id="QT-UTF8-010",
            severity="info",
            message="o",
            location="C:\\x\\b.cpp:3",
        ),
    ]


def test_findings_sarif_when_rendered_then_rules_levels_and_regions():
    sarif = json.loads(report.findings_sarif(_findings()))
    run = sarif["runs"][0]
    assert sarif["version"] == "2.1.0" and run["tool"]["driver"]["name"] == "localizzy"
    assert [rule["id"] for rule in run["tool"]["driver"]["rules"]] == [
        "QT-TR-002",
        "CUSTOM",
        "QT-UTF8-010",
    ], "one descriptor per rule that occurs"
    first = run["results"][0]
    region = first["locations"][0]["physicalLocation"]["region"]
    assert first["level"] == "error" and region == {"startLine": 10, "startColumn": 5}
    windows = run["results"][2]["locations"][0]["physicalLocation"]
    assert windows["artifactLocation"]["uri"] == "C:\\x\\b.cpp", "drive letter kept"
    assert "locations" not in run["results"][1], "no location, no SARIF location"


def test_render_when_table_json_or_unknown_format():
    table = report.render(_findings(), "table", title="T")
    assert table.splitlines()[0] == "T" and "3 finding(s)" in table, table
    assert json.loads(report.render(_findings(), "json"))[1]["unit_key"] == "k"
    with pytest.raises(ValueError, match="format"):
        report.render([], "xml")


def test_blocking_when_threshold_then_filters_and_rejects_unknown():
    assert [f.rule_id for f in report.blocking(_findings(), "major")] == ["QT-TR-002"]
    assert len(report.blocking(_findings(), "info")) == 3
    with pytest.raises(ValueError, match="fail_on"):
        report.blocking([], "fatal")


def test_emit_when_out_given_then_file_written(tmp_path, capsys):
    out = tmp_path / "findings.sarif"
    report.emit(_findings(), "sarif", out)
    assert json.loads(out.read_text())["runs"][0]["results"], "SARIF written to --out"
    assert "wrote" in capsys.readouterr().out


def test_find_tool_when_missing_then_not_found_and_require_raises(monkeypatch):
    monkeypatch.setattr(external.shutil, "which", lambda name: None)
    monkeypatch.setattr(external, "_qt_search_dirs", lambda: [])
    assert not external.find_tool("lupdate").found, "nothing on PATH or in Qt dirs"
    with pytest.raises(external.MissingDependencyError, match="lupdate") as caught:
        external.require_tool("lupdate")
    assert caught.value.how, "the error carries an install hint"


def test_extra_installed_when_known_and_unknown_extra():
    assert external.extra_installed("review") is True, (
        "the test environment has fastapi"
    )
    assert external.extra_installed("no-such-extra") is False
    assert "vexy-localizzy[clang]" in external.install_command("clang")


def test_doctor_when_tools_missing_then_suggestions(monkeypatch):
    monkeypatch.setattr(
        doctor, "find_tool", lambda name: external.ToolInfo(name, None, None)
    )
    monkeypatch.setattr(doctor, "extra_installed", lambda extra: extra != "clang")
    result = doctor.run()
    text = doctor.render(result)
    assert not result.tools["lupdate"]["found"] and result.extras["clang"] is False
    assert "MISSING" in text and "[clang] extra" in text, text
    assert len(result.suggestions) == len(set(result.suggestions)), "no duplicates"


def test_parse_icu_plural_when_nested_placeholders_and_offset_then_arms_whole():
    text = "{n, plural, offset:1 =0 {none} one {{name} has # file} other {{name} has # files}}"
    parsed = plurals.parse_icu_plural(text)
    assert parsed.forms == {
        "zero": "none",
        "one": "{name} has # file",
        "other": "{name} has # files",
    }, parsed.forms
