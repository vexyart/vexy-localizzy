# this_file: tests/upgrade/test_upgrade_identity.py
"""Identity pairing: ids, duplicates, numerus shape and form counts."""

from upgrade_helpers import by_source, context, doc, message, new_message

from vexy_localizzy.formats import ts_xml as xml
from vexy_localizzy.upgrade import (
    UpgradeOptions,
    identity,
    message_refs,
    upgrade_ts,
)

NO_ENGINE = UpgradeOptions(no_engine=True)


def forms(count: int, *texts: str) -> str:
    rows = [f"                <numerusform>{t}</numerusform>\n" for t in texts]
    rows += ["                <numerusform></numerusform>\n"] * (count - len(texts))
    return "\n" + "".join(rows) + "            "


def test_identity_when_id_present_then_id_key_else_triple():
    refs = message_refs(
        doc(
            context(
                "C",
                message("A", attrs=' id="a.one"'),
                message("B", extra="            <comment>verb</comment>\n"),
            )
        )
    )
    assert identity(refs[0]) == ("id", "a.one")
    assert identity(refs[1]) == ("key", "C", "B", "verb")


def test_upgrade_when_id_matches_but_source_changed_then_fuzzy_not_exact():
    approved = doc(
        context(
            "C",
            message("Open file...", "Datei öffnen …", attrs=' id="open"'),
            message("Delete everything now", "Alles jetzt löschen", attrs=' id="del"'),
        )
    )
    fresh = doc(
        context(
            "Other",
            message("Open file…", unfinished=True, attrs=' id="open"'),
            message("Remove selection", unfinished=True, attrs=' id="del"'),
        )
    )
    result = upgrade_ts(fresh, approved, options=NO_ENGINE)
    outcomes = by_source(result.report)
    assert outcomes["Open file…"].category == "fuzzy_exact_loose"
    assert outcomes["Remove selection"].category == "fuzzy_similar"
    assert outcomes["Remove selection"].similarity < 0.92, "an id pins the pair"
    element = new_message(result.new_bytes, "Remove selection")
    assert element.findtext("oldsource") == "Delete everything now"
    assert result.report.retired_ordinals == []


def test_upgrade_when_fresh_id_unknown_to_approved_then_key_match():
    approved = doc(context("C", message("Open", "Öffnen")))
    fresh = doc(context("C", message("Open", unfinished=True, attrs=' id="open"')))
    result = upgrade_ts(fresh, approved, options=NO_ENGINE)
    assert by_source(result.report)["Open"].category == "exact"


def test_upgrade_when_duplicate_identities_then_paired_by_order():
    approved = doc(context("C", message("Same", "Erste"), message("Same", "Zweite")))
    fresh = doc(
        context("C", message("Same", unfinished=True), message("Same", unfinished=True))
    )
    result = upgrade_ts(fresh, approved, options=NO_ENGINE)
    targets = [
        xml.text(r.element.find("translation"), "")
        for r in message_refs(result.new_bytes)
    ]
    assert targets == ["Erste", "Zweite"]
    assert [m.approved_ordinal for m in result.report.messages] == [0, 1]


def test_upgrade_when_numerus_forms_match_then_exact():
    approved = doc(
        context(
            "C",
            message(
                "%n file(s)", forms(2, "%n Datei", "%n Dateien"), attrs=' numerus="yes"'
            ),
        )
    )
    fresh = doc(
        context(
            "C",
            message("%n file(s)", forms(2), unfinished=True, attrs=' numerus="yes"'),
        )
    )
    result = upgrade_ts(fresh, approved, options=NO_ENGINE)
    assert result.report.messages[0].category == "exact"
    element = new_message(result.new_bytes, "%n file(s)")
    assert [xml.text(f, "") for f in element.iter("numerusform")] == [
        "%n Datei",
        "%n Dateien",
    ]


def test_upgrade_when_fresh_has_more_forms_then_plural_count_changed():
    approved = doc(
        context(
            "C",
            message(
                "%n file(s)", forms(2, "%n plik", "%n pliki"), attrs=' numerus="yes"'
            ),
        ),
        language="pl_PL",
    )
    fresh = doc(
        context(
            "C",
            message("%n file(s)", forms(3), unfinished=True, attrs=' numerus="yes"'),
        ),
        language="pl_PL",
    )
    result = upgrade_ts(fresh, approved, options=NO_ENGINE)
    outcome = result.report.messages[0]
    assert outcome.category == "plural_count_changed"
    assert outcome.state == "unfinished"
    element = new_message(result.new_bytes, "%n file(s)")
    assert [xml.text(f, "") for f in element.iter("numerusform")] == [
        "%n plik",
        "%n pliki",
        "",
    ]


def test_upgrade_when_fresh_has_no_forms_then_qt_count_used():
    approved = doc(
        context(
            "C",
            message(
                "%n file(s)", forms(2, "%n plik", "%n pliki"), attrs=' numerus="yes"'
            ),
        ),
        language="pl_PL",
    )
    fresh = doc(
        context("C", message("%n file(s)", unfinished=True, attrs=' numerus="yes"')),
        language="pl_PL",
    )
    result = upgrade_ts(fresh, approved, options=NO_ENGINE)
    assert result.report.messages[0].category == "plural_count_changed", (
        "Polish has 3 Qt forms"
    )


def test_upgrade_when_numerus_flips_then_shape_changed_and_candidate_retired():
    approved = doc(context("C", message("%n master(s)", "%n Master")))
    fresh = doc(
        context(
            "C",
            message("%n master(s)", forms(2), unfinished=True, attrs=' numerus="yes"'),
        )
    )
    result = upgrade_ts(fresh, approved, options=NO_ENGINE)
    outcome = result.report.messages[0]
    assert outcome.category == "shape_changed"
    assert not outcome.filled
    assert result.report.retired_ordinals == [0], "shape_changed never consumes"
    assert result.report.invariants["approved_consumed_or_retired"]
