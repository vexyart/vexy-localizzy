# this_file: tests/test_classification_result_boundaries.py
"""Reconcile actual inputs and hold a consistent decision snapshot through export."""

import json
import sqlite3
from xml.etree import ElementTree as ET

import pytest
from classification_fixtures import completed_run as completed_run
from classification_fixtures import rewrite_input, seal_fixture

from vexy_localizzy.classification_export import export_ab
from vexy_localizzy.classification_results import validated_results
from vexy_localizzy.corpus import Corpus


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate_id",
        "zero_id",
        "huge_id",
        "empty_locales",
        "duplicate_locale",
        "coverage",
        "entries",
        "source_snapshot",
    ],
)
def test_results_when_input_and_run_agree_but_contents_invalid_then_reject(
    completed_run, damage
):
    directory, inputs, _ = completed_run
    rows = [json.loads(line) for line in inputs.read_text().splitlines()]
    match damage:
        case "duplicate_id":
            rows[2]["id"] = 1
        case "zero_id":
            rows[1]["id"] = 0
        case "huge_id":
            rows[-1]["id"] = 2**63
        case "empty_locales":
            rows[1]["locales"] = []
        case "duplicate_locale":
            rows[1]["locales"] = ["pl", "pl"]
        case "coverage":
            rows[0]["coverage"]["pl"] = 99
        case "entries":
            rows[0]["entries"] = 99
        case "source_snapshot":
            rows[0]["source_snapshot"] = "0" * 64
    rewrite_input(directory, inputs, rows)
    with pytest.raises(ValueError):
        with validated_results(directory, inputs):
            pytest.fail(
                "Internally inconsistent input must fail even with a matching hash"
            )


def test_results_when_decisions_change_after_check_then_selection_uses_checked_snapshot(
    completed_run,
):
    directory, inputs, _ = completed_run
    with sqlite3.connect(directory / "decisions.sqlite") as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        with validated_results(directory, inputs) as result:
            writer.execute("UPDATE decisions SET class='C' WHERE entry_id=1")
            writer.commit()
            assert list(result.selected_ids()) == [1, 2, 4]
        with pytest.raises(ValueError, match="votes/policy"):
            with validated_results(directory, inputs):
                pytest.fail("A new reader must reject changed decision evidence")


def test_export_when_no_ab_sources_then_empty_tmx_not_all_winners(
    completed_run, tmp_path
):
    directory, inputs, database = completed_run
    with sqlite3.connect(directory / "decisions.sqlite") as db:
        db.execute(
            "UPDATE decisions SET class='C',votes='[\"C\",\"C\",\"C\"]',reason='majority',disagreement=0"
        )
    marker = json.loads((directory / "complete.json").read_text())
    marker["classes"] = {"C": 4}
    (directory / "complete.json").write_text(json.dumps(marker))
    seal_fixture(directory)
    output = tmp_path / "ab.tmx"
    with Corpus(database) as corpus:
        report = export_ab(corpus, directory, inputs, output)
    assert report["selected_entries"] == report["units"] == 0
    assert ET.parse(output).findall("body/tu") == []


def test_export_when_legacy_input_then_explicit_binding_required(
    completed_run, tmp_path
):
    directory, inputs, database = completed_run
    rows = [json.loads(line) for line in inputs.read_text().splitlines()]
    mapping = rows[0].pop("entry_map_sha256")
    rewrite_input(directory, inputs, rows)
    output = tmp_path / "ab.tmx"
    with Corpus(database) as corpus:
        with pytest.raises(ValueError, match="audited entry map"):
            export_ab(corpus, directory, inputs, output)
        assert not output.exists()
        report = export_ab(corpus, directory, inputs, output, entry_map_sha256=mapping)
        assert report["entry_map_sha256"] == mapping
        assert report["units"] == 4


def test_export_when_binding_conflicts_with_header_then_preserve_output(
    completed_run, tmp_path
):
    directory, inputs, database = completed_run
    output = tmp_path / "ab.tmx"
    output.write_text("previous")
    with Corpus(database) as corpus, pytest.raises(ValueError, match="Conflicting"):
        export_ab(corpus, directory, inputs, output, entry_map_sha256="f" * 64)
    assert output.read_text() == "previous"


def test_results_when_another_runs_decisions_replace_db_then_reject_even_matching_counts(
    completed_run,
):
    directory, inputs, _ = completed_run
    with sqlite3.connect(directory / "decisions.sqlite") as db:
        db.execute(
            'UPDATE decisions SET class=\'C\',votes=\'["C","C","C"]\' WHERE entry_id=1'
        )
        db.execute(
            'UPDATE decisions SET class=\'A\',votes=\'["A","A","A"]\' WHERE entry_id=3'
        )
    with pytest.raises(ValueError, match="decision.*digest"):
        with validated_results(directory, inputs):
            pytest.fail("Different valid decisions cannot inherit another run identity")


def test_results_when_legacy_marker_has_no_decision_binding_then_require_producer_upgrade(
    completed_run,
):
    directory, inputs, _ = completed_run
    path = directory / "complete.json"
    marker = json.loads(path.read_text())
    del marker["decision_sha256"]
    path.write_text(json.dumps(marker))
    with pytest.raises(ValueError, match="decision_sha256"):
        with validated_results(directory, inputs):
            pytest.fail(
                "A fresh digest must not silently bless unbound legacy evidence"
            )


def test_decision_digest_when_producer_seals_rows_then_matches_independent_fixture(
    completed_run,
):
    from vexy_localizzy.classification_results import decision_digest

    directory, _, _ = completed_run
    expected = json.loads((directory / "complete.json").read_text())["decision_sha256"]
    with sqlite3.connect(directory / "decisions.sqlite") as db:
        db.execute("BEGIN")
        assert decision_digest(db) == expected


def test_results_when_complete_flag_is_integer_then_reject(completed_run):
    directory, inputs, _ = completed_run
    path = directory / "complete.json"
    marker = json.loads(path.read_text())
    marker["complete"] = 1
    path.write_text(json.dumps(marker))
    with pytest.raises(ValueError, match="complete"):
        with validated_results(directory, inputs):
            pytest.fail("Completion must be an explicit boolean")


def test_export_when_classified_text_differs_from_bound_corpus_then_reject(
    completed_run, tmp_path
):
    directory, inputs, database = completed_run
    rows = [json.loads(line) for line in inputs.read_text().splitlines()]
    rows[1]["text"] = "Different text classified under the same numeric ID"
    rewrite_input(directory, inputs, rows)
    output = tmp_path / "ab.tmx"
    output.write_text("previous")
    with Corpus(database) as corpus, pytest.raises(ValueError, match="source text"):
        export_ab(corpus, directory, inputs, output)
    assert output.read_text() == "previous"
