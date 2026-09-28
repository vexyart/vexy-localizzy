# this_file: tests/test_classification_results.py
"""Only fully reconciled classifications may drive a complete A/B export."""

import hashlib
import json
import sqlite3
from collections import Counter
from xml.etree import ElementTree as ET

import pytest
from classification_fixtures import completed_run as completed_run
from classification_fixtures import seal_fixture

from vexy_localizzy.classification_export import export_ab
from vexy_localizzy.classification_results import validated_results
from vexy_localizzy.corpus import Corpus


def test_results_when_complete_then_export_all_ab_targets_and_replay_rare_promotion(
    completed_run, tmp_path
):
    directory, inputs, database = completed_run
    with validated_results(directory, inputs) as result:
        assert list(result.selected_ids()) == [1, 2, 4]
        assert result.report["classes"] == {"A": 1, "B": 2, "C": 1}
        assert result.report["fully_reported_entries"] == 4
    output = tmp_path / "ab.tmx"
    with Corpus(database) as corpus:
        report = export_ab(corpus, directory, inputs, output)
    assert report["selected_entries"] == 3 and report["units"] == 4
    assert report["output_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    ids = [
        int(tu.find("prop[@type='x-vexy-localizzy-source-id']").text)
        for tu in ET.parse(output).findall("body/tu")
    ]
    assert Counter(ids) == {1: 1, 2: 1, 4: 2}, (
        "Rare-language winners must survive the A/B handoff"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "DELETE FROM decisions WHERE entry_id=4",
        "UPDATE decisions SET entry_id=99 WHERE entry_id=4",
        "UPDATE decisions SET class='C' WHERE entry_id=4",
        'UPDATE decisions SET votes=\'["C","C","C"]\' WHERE entry_id=4',
        "UPDATE decisions SET reason='invented' WHERE entry_id=1",
        "UPDATE decisions SET disagreement=1 WHERE entry_id=1",
        "DELETE FROM decision_models WHERE entry_id=1",
        "INSERT INTO decision_models SELECT 99,models,requested_models,reported_models,identity_verified FROM decision_models LIMIT 1",
        'UPDATE decision_models SET models=\'["one","two","unknown"]\'',
        'UPDATE decision_models SET reported_models=\'["one","one","spare"]\'',
        'UPDATE decision_models SET requested_models=\'["one","two","spare"]\'',
        "UPDATE decision_models SET identity_verified=0",
        "INSERT INTO pending_batches VALUES ('pending','[1]','offline',0)",
    ],
)
def test_results_when_evidence_inconsistent_then_old_output_preserved(
    completed_run, tmp_path, mutation
):
    directory, inputs, database = completed_run
    with sqlite3.connect(directory / "decisions.sqlite") as db:
        db.execute(mutation)
    output = tmp_path / "ab.tmx"
    output.write_text("previous")
    with Corpus(database) as corpus, pytest.raises(ValueError):
        export_ab(corpus, directory, inputs, output)
    assert output.read_text() == "previous"


@pytest.mark.parametrize(
    "damage",
    [
        "missing_marker",
        "false_marker",
        "wrong_run",
        "wrong_counts",
        "changed_input",
        "changed_policy",
    ],
)
def test_results_when_completion_or_input_changed_then_reject(completed_run, damage):
    directory, inputs, _ = completed_run
    marker = directory / "complete.json"
    data = json.loads(marker.read_text())
    if damage == "missing_marker":
        marker.unlink()
    elif damage == "changed_input":
        inputs.write_bytes(inputs.read_bytes() + b"\n")
    elif damage == "changed_policy":
        identity = directory / "identity.json"
        data = json.loads(identity.read_text())
        data["rare_threshold"] = 0.1
        identity.write_text(json.dumps(data))
    else:
        data.update(
            {
                "false_marker": {"complete": False},
                "wrong_run": {"run_id": "f" * 64},
                "wrong_counts": {"classes": {"A": 4}},
            }[damage]
        )
        marker.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        with validated_results(directory, inputs):
            pytest.fail("Damaged evidence must not be exposed as complete")


def test_results_when_legacy_reports_unknown_then_keep_unknown_with_explicit_identity_map(
    completed_run,
):
    directory, inputs, _ = completed_run
    with sqlite3.connect(directory / "decisions.sqlite") as db:
        db.execute("UPDATE decision_models SET reported_models='[null,null,null]'")
    seal_fixture(directory)
    with validated_results(directory, inputs) as result:
        assert result.report["fully_reported_entries"] == 0
        assert result.report["entries"] == 4


def test_export_when_destination_is_evidence_then_refuse_replacement(completed_run):
    directory, inputs, database = completed_run
    before = inputs.read_bytes()
    with Corpus(database) as corpus, pytest.raises(ValueError, match="evidence"):
        export_ab(corpus, directory, inputs, inputs)
    assert inputs.read_bytes() == before
