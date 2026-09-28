# this_file: tests/classification_fixtures.py
"""Complete synthetic corpus/run evidence for handoff tests."""

import hashlib
import json
import sqlite3
from collections import Counter

import pytest

from vexy_localizzy.classification import consensus
from vexy_localizzy.classification_inputs import prepare_inputs
from vexy_localizzy.corpus.store import Corpus


@pytest.fixture
def completed_run(tmp_path):
    source = tmp_path / "source.tmx"
    source.write_text(
        "<tmx><body>"
        + "".join(
            f'<tu><tuv lang="en"><seg>Source {i}</seg></tuv>'
            f'<tuv lang="pl"><seg>Target {i}</seg></tuv>'
            + ('<tuv lang="cy"><seg>Rare target</seg></tuv>' if i == 4 else "")
            + "</tu>"
            for i in range(1, 5)
        )
        + "</body></tmx>"
    )
    with Corpus(tmp_path / "corpus.sqlite") as corpus:
        corpus.import_tmx(source, family="synthetic", weight=3)
        inputs = tmp_path / "inputs.jsonl"
        metadata = prepare_inputs(corpus, inputs)
    identity = {
        "input_sha256": hashlib.sha256(inputs.read_bytes()).hexdigest(),
        "source_snapshot": metadata["source_snapshot"],
        "models": ["one", "two", "three"],
        "fallbacks": {"three": ["spare"]},
        "model_identities": {
            "one": "one",
            "two": "two",
            "three": "three",
            "spare": "spare",
        },
        "endpoint": "https://example.test/v1",
        "prompt_sha256": "a" * 64,
        "rare_threshold": 0.5,
        "consensus_version": 1,
    }
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    directory = tmp_path / run_id
    directory.mkdir()
    (directory / "identity.json").write_text(json.dumps(identity))
    classes = Counter()
    with sqlite3.connect(directory / "decisions.sqlite") as db:
        db.executescript("""
        CREATE TABLE decisions(entry_id INTEGER PRIMARY KEY,class TEXT,votes TEXT,reason TEXT,disagreement INTEGER);
        CREATE TABLE decision_models(entry_id INTEGER PRIMARY KEY,models TEXT,requested_models TEXT,reported_models TEXT,identity_verified INTEGER);
        CREATE TABLE pending_batches(key TEXT PRIMARY KEY,ids TEXT,error TEXT,updated REAL);
        """)
        for row, votes in zip(
            [json.loads(s) for s in inputs.read_text().splitlines()[1:]],
            [["A"] * 3, ["B"] * 3, ["C"] * 3, ["B", "C", "C"]],
            strict=True,
        ):
            decision = consensus(votes, tuple(row["locales"]), {"cy"})
            classes[decision["class"]] += 1
            db.execute(
                "INSERT INTO decisions VALUES (?,?,?,?,?)",
                (
                    row["id"],
                    decision["class"],
                    json.dumps(votes),
                    decision["reason"],
                    decision["disagreement"],
                ),
            )
            db.execute(
                "INSERT INTO decision_models VALUES (?,?,?,?,?)",
                (
                    row["id"],
                    '["one","two","spare"]',
                    '["one","two","three"]',
                    '["one","two","spare"]',
                    1,
                ),
            )
    (directory / "complete.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "entries": 4,
                "expected_entries": 4,
                "pending_entries": 0,
                "complete": True,
                "classes": classes,
                "rare_locales": ["cy"],
            }
        )
    )
    seal_fixture(directory)
    return directory, inputs, tmp_path / "corpus.sqlite"


def seal_fixture(directory):
    """Emulate the producer freezing exact ordered evidence at completion."""
    digest = hashlib.sha256()
    with sqlite3.connect(directory / "decisions.sqlite") as db:
        for row in db.execute(
            "SELECT d.entry_id,d.class,d.votes,d.reason,d.disagreement,m.models,m.requested_models,m.reported_models,m.identity_verified FROM decisions d JOIN decision_models m USING(entry_id) ORDER BY d.entry_id"
        ):
            digest.update(
                json.dumps(
                    list(row), ensure_ascii=False, separators=(",", ":")
                ).encode()
                + b"\n"
            )
    path = directory / "complete.json"
    marker = json.loads(path.read_text())
    marker["decision_sha256"] = digest.hexdigest()
    path.write_text(json.dumps(marker))


def rewrite_input(directory, inputs, rows):
    inputs.write_text("".join(json.dumps(row) + "\n" for row in rows))
    identity = json.loads((directory / "identity.json").read_text())
    identity["input_sha256"] = hashlib.sha256(inputs.read_bytes()).hexdigest()
    (directory / "identity.json").write_text(json.dumps(identity))
    marker = json.loads((directory / "complete.json").read_text())
    marker["run_id"] = hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode()
    ).hexdigest()
    (directory / "complete.json").write_text(json.dumps(marker))
