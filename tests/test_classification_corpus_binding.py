# this_file: tests/test_classification_corpus_binding.py
"""Full corpus eligibility, including rare targets, must match the frozen input."""

import json
import sqlite3

import pytest
from classification_fixtures import completed_run as completed_run
from classification_fixtures import rewrite_input, seal_fixture

from vexy_localizzy.classification_export import export_ab
from vexy_localizzy.corpus import Corpus


@pytest.mark.parametrize("damage", ["omitted_source", "omitted_rare_target"])
def test_export_when_self_consistent_input_omits_corpus_evidence_then_reject(
    completed_run, tmp_path, damage
):
    directory, inputs, database = completed_run
    rows = [json.loads(line) for line in inputs.read_text().splitlines()]
    marker = json.loads((directory / "complete.json").read_text())
    with sqlite3.connect(directory / "decisions.sqlite") as db:
        if damage == "omitted_source":
            del rows[1]
            rows[0]["entries"] = 3
            rows[0]["coverage"]["pl"] = 3
            db.execute("DELETE FROM decisions WHERE entry_id=1")
            db.execute("DELETE FROM decision_models WHERE entry_id=1")
            marker.update(entries=3, expected_entries=3, classes={"B": 2, "C": 1})
        else:
            rows[-1]["locales"] = ["pl"]
            del rows[0]["coverage"]["cy"]
            db.execute(
                "UPDATE decisions SET class='C',reason='majority' WHERE entry_id=4"
            )
            marker.update(classes={"A": 1, "B": 1, "C": 2}, rare_locales=[])
    (directory / "complete.json").write_text(json.dumps(marker))
    rewrite_input(directory, inputs, rows)
    seal_fixture(directory)
    output = tmp_path / "ab.tmx"
    output.write_text("previous")
    with Corpus(database) as corpus, pytest.raises(ValueError, match="corpus"):
        export_ab(corpus, directory, inputs, output)
    assert output.read_text() == "previous"
