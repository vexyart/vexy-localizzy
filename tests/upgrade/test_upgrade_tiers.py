# this_file: tests/upgrade/test_upgrade_tiers.py
"""Tier classification and element ownership on the synthetic fixture pair."""

import pytest
from upgrade_helpers import (
    APPROVED,
    FRESH,
    by_source,
    context,
    direct_memory,
    doc,
    fresh_side_unchanged,
    glossary,
    message,
    new_message,
    report_accounts_for_approved,
)

from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.formats.ts_read import load_bytes
from vexy_localizzy.upgrade import UpgradeOptions, message_refs, upgrade_ts
from vexy_localizzy.upgrade.report import TIER_CATEGORIES

NO_ENGINE = UpgradeOptions(no_engine=True)


@pytest.fixture(scope="module")
def result():
    return upgrade_ts(
        FRESH.read_bytes(),
        APPROVED.read_bytes(),
        direct=direct_memory(),
        glossary=glossary(),
        options=NO_ENGINE,
    )


def test_upgrade_when_identity_run_then_bytes_identical_and_all_exact():
    raw = APPROVED.read_bytes()
    result = upgrade_ts(raw, raw, options=NO_ENGINE)
    assert result.new_bytes == raw, "NEW must equal the input byte for byte"
    retired = load_bytes(result.retired_bytes).units
    assert [u.state for u in retired] == ["vanished"], (
        "only the obsolete message retires"
    )
    active = [m for m in result.report.messages if m.category != "excluded_vanished"]
    assert {m.category for m in active} <= {"exact", "exact_unfinished"}
    assert result.report.counts["retired_active"] == 0
    assert result.report.counts["retired_obsolete"] == 1, "vanished APPROVED retires"


def test_upgrade_when_identity_run_with_empty_unfinished_then_bytes_identical():
    raw = FRESH.read_bytes()  # holds empty scalar and empty numerus translations
    result = upgrade_ts(raw, raw, options=NO_ENGINE)
    assert result.new_bytes == raw, "empty unfinished messages must not re-render"
    assert result.report.counts["untranslated"] > 0


def test_upgrade_when_location_changed_then_exact_with_fresh_location(result):
    outcome = by_source(result.report)["Open"]
    assert outcome.category == "exact"
    element = new_message(result.new_bytes, "Open")
    location = element.find("location")
    assert location.get("line") == "+12", "NEW keeps FRESH's location"
    assert xml.text(element.find("translation"), "") == "Öffnen"
    assert element.find("translation").get("type") is None, "finished state copied"


def test_upgrade_when_approved_unfinished_then_exact_unfinished(result):
    outcome = by_source(result.report)["Close"]
    assert outcome.category == "exact_unfinished"
    assert outcome.state == "unfinished"


def test_upgrade_when_context_renamed_then_relocated_unfinished(result):
    outcome = by_source(result.report)["Rename layer"]
    assert outcome.category == "relocated"
    assert outcome.state == "unfinished"
    element = new_message(result.new_bytes, "Rename layer")
    assert xml.text(element.find("translation"), "") == "Ebene umbenennen"


def test_upgrade_when_relocated_finished_option_then_finished():
    result = upgrade_ts(
        FRESH.read_bytes(),
        APPROVED.read_bytes(),
        options=UpgradeOptions(no_engine=True, relocated_finished=True),
    )
    assert by_source(result.report)["Rename layer"].state == "finished"


@pytest.mark.parametrize(
    ("fresh", "old"), [("Save as…", "Save as..."), ("Export", "Export:")]
)
def test_upgrade_when_cosmetic_source_change_then_fuzzy_loose_with_oldsource(
    result, fresh, old
):
    outcome = by_source(result.report)[fresh]
    assert outcome.category == "fuzzy_exact_loose"
    assert outcome.approved_source == old
    element = new_message(result.new_bytes, fresh)
    assert element.findtext("oldsource") == old
    children = [child.tag for child in element]
    assert children.index("oldsource") == children.index("source") + 1


def test_upgrade_when_one_word_edit_then_fuzzy_similar(result):
    outcome = by_source(result.report)["Show kerning pair panel"]
    assert outcome.category == "fuzzy_similar"
    assert outcome.similarity >= 0.92
    assert outcome.state == "unfinished"


def test_upgrade_when_two_equally_close_candidates_then_not_fuzzy(result):
    outcome = by_source(result.report)["Snap to grid X"]
    assert outcome.category == "untranslated", "a tie must never pick a candidate"
    assert not outcome.filled


def test_upgrade_when_memory_context_hit_then_finished(result):
    outcome = by_source(result.report)["Units"]
    assert outcome.category == "memory_context"
    assert outcome.state == "finished"
    assert outcome.tuids == ["Preferences|Units"]
    element = new_message(result.new_bytes, "Units")
    assert xml.text(element.find("translation"), "") == "Einheiten"


def test_upgrade_when_whole_glossary_term_then_memory_term_finished(result):
    outcome = by_source(result.report)["Glyph"]
    assert outcome.category == "memory_term"
    assert outcome.state == "finished"


def test_upgrade_when_finish_on_excludes_context_then_memory_hit_unfinished():
    result = upgrade_ts(
        FRESH.read_bytes(),
        APPROVED.read_bytes(),
        direct=direct_memory(),
        options=UpgradeOptions(no_engine=True, finish_on=frozenset({"id"})),
    )
    assert by_source(result.report)["Units"].state == "unfinished"


def test_upgrade_when_translator_metadata_then_carried_and_extracomment_fresh(result):
    element = new_message(result.new_bytes, "Metrics")
    assert element.findtext("translatorcomment") == "Use Metrik, not Maße."
    assert element.findtext("extra-po-flags") == "no-c-format"
    assert element.findtext("extracomment") == "new developer note"
    order = [child.tag for child in element]
    assert order == [
        "location",
        "source",
        "extracomment",
        "translatorcomment",
        "translation",
        "extra-po-flags",
    ]


def test_upgrade_when_message_removed_then_retired(result):
    retired = {r.source: r for r in message_refs(result.retired_bytes)}
    assert "Quit" in retired
    location = retired["Quit"].element.find("location")
    assert dict(location.attrib) == {"filename": "../src/menu.cpp", "line": "20"}
    assert "Legacy option" in retired, "APPROVED obsolete messages retire"
    assert retired["Legacy option"].kind == "vanished", "translation type is kept"
    assert result.report.counts["retired_obsolete"] == 1


def test_upgrade_when_empty_source_then_excluded_and_untouched(result):
    outcome = next(m for m in result.report.messages if m.source == "")
    assert outcome.category == "excluded_empty"
    assert outcome.state == "untouched"


def test_upgrade_when_changed_then_only_changed_lines_differ(result):
    fresh = FRESH.read_bytes().decode().splitlines()
    new = result.new_bytes.decode().splitlines()
    assert new[:3] == fresh[:3], "declaration, doctype and TS tag are FRESH's"
    unchanged = message_refs(FRESH.read_bytes())
    assert len(message_refs(result.new_bytes)) == len(unchanged)


def test_upgrade_invariants_when_run_then_counts_sum_to_active(result):
    report = result.report
    assert report.invariants == {
        "every_fresh_classified": True,
        "approved_consumed_or_retired": True,
    }
    active = sum(1 for r in message_refs(FRESH.read_bytes()) if r.active)
    assert sum(report.counts[c] for c in TIER_CATEGORIES) == active
    consumed = {
        m.approved_ordinal for m in report.messages if m.approved_ordinal is not None
    }
    consumed -= {
        m.approved_ordinal for m in report.messages if m.category == "shape_changed"
    }
    assert len(consumed) + len(report.retired_ordinals) == report.approved.messages


def test_upgrade_when_target_given_then_language_rewritten():
    raw = APPROVED.read_bytes()
    result = upgrade_ts(raw, raw, target="de", options=NO_ENGINE)
    assert b'language="de"' in result.new_bytes.splitlines()[2]
    assert result.report.target_lang == "de"


def test_upgrade_when_sourcelanguage_differs_then_usage_error():
    from vexy_localizzy.upgrade import UpgradeUsageError

    fresh = doc(context("C", message("A")), source="fr")
    approved = doc(context("C", message("A", "a")))
    with pytest.raises(UpgradeUsageError, match="sourcelanguage"):
        upgrade_ts(fresh, approved, options=NO_ENGINE)


def test_upgrade_file_when_invariant_fails_then_nothing_written(tmp_path, monkeypatch):
    from vexy_localizzy.upgrade import UpgradeInvariantError, ts_upgrade, upgrade

    monkeypatch.setattr(
        ts_upgrade, "invariants", lambda *a: {"every_fresh_classified": False}
    )
    out, retired = tmp_path / "n.ts", tmp_path / "r.ts"
    with pytest.raises(UpgradeInvariantError):
        upgrade(FRESH, APPROVED, out=out, retired=retired, options=NO_ENGINE)
    assert not out.exists() and not retired.exists()


def test_report_when_run_then_accounts_for_every_approved_message(result):
    assert report_accounts_for_approved(result.report)


def test_report_when_identity_run_with_empty_approved_then_still_accounted():
    raw = FRESH.read_bytes()  # empty-text APPROVED candidates and an empty source
    report = upgrade_ts(raw, raw, options=NO_ENGINE).report
    assert report_accounts_for_approved(report)
    empty = next(m for m in report.messages if m.category == "excluded_empty")
    assert empty.approved_ordinal is not None


def test_upgrade_when_ported_then_only_translation_side_changes(result):
    changed = fresh_side_unchanged(FRESH.read_bytes(), result.new_bytes)
    assert changed > 0
