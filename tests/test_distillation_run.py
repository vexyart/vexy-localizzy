# this_file: tests/test_distillation_run.py
"""Complete pass accounting, durable resume and protected cross-chunk replacements."""

import json
import sqlite3
from collections import Counter

import numpy as np
import pytest

from vexy_localizzy.distillation import DistillationEntry
from vexy_localizzy.distillation_cache import CachedSelector
from vexy_localizzy.distillation_run import ClusterEntry, retained_items, run_pass
from vexy_localizzy.translate.provider_errors import ModelResponse, ProviderUnavailable


def items(count=5):
    return [
        ClusterEntry(
            0,
            DistillationEntry(
                id=i,
                source=f"Action {i}",
                targets={"de": f"Aktion {i}"},
                criticality="A",
                quality=3,
            ),
            np.array([1, 0], dtype=np.float32),
        )
        for i in range(1, count + 1)
    ]


def reply(model, _prompt, payload):
    rows = json.loads(payload)["entries"]
    return ModelResponse(
        json.dumps(
            {
                "keep": [rows[0]["id"]],
                "drop": [
                    {
                        "id": row["id"],
                        "representative": rows[0]["id"],
                        "equivalent": True,
                        "reason": "Equivalent action",
                    }
                    for row in rows[1:]
                ],
            }
        ),
        model,
    )


def options():
    return {
        "source_identity": {"snapshot": "synthetic-corpus-v1"},
        "embedding_identity": {"dimensions": 2, "space": "synthetic"},
        "rare_locales": set(),
        "max_entries": 2,
        "carry": 1,
    }


def selector(path, request=reply):
    return CachedSelector(
        path,
        models=("one", "two", "three"),
        request=request,
        endpoint_identity="synthetic",
    )


def test_pass_when_cluster_split_then_carry_and_complete_id_accounting(tmp_path):
    batches = []

    def request(model, prompt, payload):
        if model == "one":
            batches.append([row["source_id"] for row in json.loads(payload)["entries"]])
        return reply(model, prompt, payload)

    output = tmp_path / "pass.sqlite"
    with selector(tmp_path / "cache.sqlite", request) as cache:
        report = run_pass(items(), cache, output, expected_count=5, **options())
        repeat = run_pass(items(), cache, output, expected_count=5, **options())
    assert report == repeat and report["complete"]
    assert report["kept"] == 1 and report["dropped"] == 4
    assert batches == [[1, 2], [1, 3], [1, 4], [1, 5]]
    assert [row.entry.id for row in retained_items(output)] == [1]
    with sqlite3.connect(output) as db:
        assert db.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 5
        assert db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 4
    assert not (tmp_path / ".pass.sqlite.pending").exists()


def test_pass_when_later_chunk_drops_used_representative_then_override(tmp_path):
    def request(model, prompt, payload):
        rows = json.loads(payload)["entries"]
        if rows[-1]["source_id"] == 3:
            return ModelResponse(
                json.dumps(
                    {
                        "keep": [301],
                        "drop": [
                            {
                                "id": 300,
                                "representative": 301,
                                "equivalent": True,
                                "reason": "New representative",
                            }
                        ],
                    }
                ),
                model,
            )
        return reply(model, prompt, payload)

    output = tmp_path / "pass.sqlite"
    with selector(tmp_path / "cache.sqlite", request) as cache:
        report = run_pass(items(3), cache, output, expected_count=3, **options())
    assert report["kept"] == 2 and report["dropped"] == 1
    with sqlite3.connect(output) as db:
        assert db.execute(
            "SELECT source_id FROM results WHERE action='keep' ORDER BY source_id"
        ).fetchall() == [(1,), (3,)]
        assert db.execute(
            "SELECT representative_id FROM results WHERE source_id=2"
        ).fetchone() == (1,)
        decisions = [
            json.loads(row[0]) for row in db.execute("SELECT decision FROM chunks")
        ]
    assert {"source_id": 1, "reason": "protected_representative"} in decisions[-1][
        "overrides"
    ]


def test_pass_when_provider_pending_then_other_clusters_finish_and_resume_missing(
    tmp_path,
):
    now, calls = [0], Counter()
    rows = items(4)
    rows = rows[:2] + [ClusterEntry(1, row.entry, row.vector) for row in rows[2:]]

    def request(model, prompt, payload):
        ids = tuple(row["source_id"] for row in json.loads(payload)["entries"])
        calls[(model, ids)] += 1
        if now[0] == 0 and ids == (1, 2) and model == "three":
            raise ProviderUnavailable("offline", retry_after=1)
        return reply(model, prompt, payload)

    output = tmp_path / "pass.sqlite"
    with selector(tmp_path / "cache.sqlite", request) as cache:
        cache.panel.clock = lambda: now[0]
        cache.select(
            [row.entry for row in rows[2:]],
            np.stack([row.vector for row in rows[2:]]),
            rare_locales=set(),
        )
        first = run_pass(rows, cache, output, expected_count=4, **options())
        assert not first["complete"] and not output.exists()
        assert first["processed"] == 2, (
            "A pending cluster must not prevent cached clusters from finishing"
        )
        now[0] = 2
        second = run_pass(rows, cache, output, expected_count=4, **options())
    assert second["complete"] and second["kept"] == 2
    assert calls[("one", (1, 2))] == calls[("two", (1, 2))] == 1
    assert calls[("three", (1, 2))] == 2


def test_pass_when_single_entry_exceeds_budget_then_retain_without_truncation(tmp_path):
    calls = []
    rows = items(2)
    oversized = rows[0].entry.model_copy(update={"source": "x" * 50000})
    rows[0] = ClusterEntry(0, oversized, rows[0].vector)
    with selector(tmp_path / "cache.sqlite", lambda *args: calls.append(args)) as cache:
        report = run_pass(
            rows, cache, tmp_path / "pass.sqlite", expected_count=2, **options()
        )
    assert report["complete"] and report["kept"] == 2 and calls == []
    assert (
        next(retained_items(tmp_path / "pass.sqlite")).entry.source == oversized.source
    )


def test_pass_when_second_unchanged_then_record_predecessor_and_no_new_votes(tmp_path):
    calls = []

    def request(model, prompt, payload):
        calls.append(model)
        return reply(model, prompt, payload)

    with selector(tmp_path / "cache.sqlite", request) as cache:
        first = run_pass(
            items(2), cache, tmp_path / "one.sqlite", expected_count=2, **options()
        )
        second = run_pass(
            retained_items(tmp_path / "one.sqlite"),
            cache,
            tmp_path / "two.sqlite",
            expected_count=1,
            predecessor=tmp_path / "one.sqlite",
            **options(),
        )
    assert first["pass_number"] == 1 and second["pass_number"] == 2
    assert second["complete"] and second["kept"] == 1 and second["predecessor_sha256"]
    assert len(calls) == 3


@pytest.mark.parametrize("change", ["text", "vector", "identity", "count", "id"])
def test_pass_when_resume_input_changes_then_refuse_before_paid_calls(tmp_path, change):
    output = tmp_path / "pass.sqlite"
    with selector(tmp_path / "cache.sqlite") as cache:
        run_pass(items(2), cache, output, expected_count=2, **options())
    original = output.read_bytes()
    rows, config, count = items(2), options(), 2
    if change == "text":
        rows[0] = ClusterEntry(
            0, rows[0].entry.model_copy(update={"source": "Changed"}), rows[0].vector
        )
    elif change == "vector":
        rows[0] = ClusterEntry(0, rows[0].entry, np.array([0, 1], dtype=np.float32))
    elif change == "identity":
        config["source_identity"] = {"snapshot": "changed"}
    elif change == "id":
        rows = [
            rows[1],
            ClusterEntry(0, rows[0].entry.model_copy(update={"id": 3}), rows[0].vector),
        ]
    else:
        count = 3
    with selector(
        tmp_path / "cache.sqlite", lambda *_: pytest.fail("No new calls allowed")
    ) as cache:
        with pytest.raises(ValueError):
            run_pass(rows, cache, output, expected_count=count, **config)
    assert output.read_bytes() == original


def test_pass_when_predecessor_retained_set_changed_then_refuse(tmp_path):
    with selector(tmp_path / "cache.sqlite") as cache:
        run_pass(
            items(2), cache, tmp_path / "one.sqlite", expected_count=2, **options()
        )
        with pytest.raises(ValueError, match="predecessor retained"):
            run_pass(
                items(2)[1:],
                cache,
                tmp_path / "two.sqlite",
                expected_count=1,
                predecessor=tmp_path / "one.sqlite",
                **options(),
            )
    assert not (tmp_path / "two.sqlite").exists()


def test_pass_when_representative_record_corrupt_then_refuse_reuse_and_predecessor(
    tmp_path,
):
    output = tmp_path / "one.sqlite"
    with selector(tmp_path / "cache.sqlite") as cache:
        run_pass(items(2), cache, output, expected_count=2, **options())
        with sqlite3.connect(output) as db:
            db.execute("UPDATE results SET representative_id=999 WHERE action='drop'")
        with pytest.raises(ValueError, match="representative"):
            run_pass(items(2), cache, output, expected_count=2, **options())
        with pytest.raises(ValueError, match="representative"):
            list(retained_items(output))


def test_pass_when_cancelled_after_completed_chunk_then_resume_remaining_only(tmp_path):
    calls = Counter()
    interrupted = [False]

    def request(model, prompt, payload):
        ids = tuple(row["source_id"] for row in json.loads(payload)["entries"])
        calls[(model, ids)] += 1
        return reply(model, prompt, payload)

    output = tmp_path / "pass.sqlite"
    with selector(tmp_path / "cache.sqlite", request) as cache:
        original = cache.select

        def select(entries, vectors, **kwargs):
            if entries[-1].id == 3 and not interrupted[0]:
                interrupted[0] = True
                raise KeyboardInterrupt
            return original(entries, vectors, **kwargs)

        cache.select = select
        with pytest.raises(KeyboardInterrupt):
            run_pass(items(3), cache, output, expected_count=3, **options())
        assert not output.exists()
        result = run_pass(items(3), cache, output, expected_count=3, **options())
    assert result["complete"] and result["kept"] == 1
    assert all(count == 1 for count in calls.values())


def test_pass_when_third_requested_then_record_it_but_reject_fourth(tmp_path):
    with selector(tmp_path / "cache.sqlite") as cache:
        prior = None
        for number in range(1, 4):
            output = tmp_path / f"{number}.sqlite"
            result = run_pass(
                items(1),
                cache,
                output,
                expected_count=1,
                predecessor=prior,
                **options(),
            )
            assert result["pass_number"] == number and result["complete"]
            prior = output
        with pytest.raises(ValueError, match="three"):
            run_pass(
                items(1),
                cache,
                tmp_path / "4.sqlite",
                expected_count=1,
                predecessor=prior,
                **options(),
            )


def test_pass_when_initialization_interrupted_then_same_path_resumes(
    tmp_path, monkeypatch
):
    from vexy_localizzy import distillation_store

    once = [True]
    connect = sqlite3.connect

    class Interrupted(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if once[0] and "INSERT INTO metadata VALUES ('identity'" in sql:
                once[0] = False
                raise KeyboardInterrupt
            return super().execute(sql, *args, **kwargs)

    with selector(tmp_path / "cache.sqlite") as cache:
        monkeypatch.setattr(
            distillation_store.sqlite3,
            "connect",
            lambda *args, **kwargs: connect(*args, factory=Interrupted, **kwargs),
        )
        with pytest.raises(KeyboardInterrupt):
            run_pass(
                items(2), cache, tmp_path / "pass.sqlite", expected_count=2, **options()
            )
        result = run_pass(
            items(2), cache, tmp_path / "pass.sqlite", expected_count=2, **options()
        )
    assert result["complete"]


def test_pass_when_dropped_input_corrupt_then_reject_predecessor(tmp_path):
    output = tmp_path / "pass.sqlite"
    with selector(tmp_path / "cache.sqlite") as cache:
        run_pass(items(2), cache, output, expected_count=2, **options())
    with sqlite3.connect(output) as db:
        data = json.loads(
            db.execute("SELECT data FROM entries WHERE source_id=2").fetchone()[0]
        )
        data["source"] = "Corrupt"
        db.execute("UPDATE entries SET data=? WHERE source_id=2", (json.dumps(data),))
    with pytest.raises(ValueError, match="Corrupt"):
        list(retained_items(output))


@pytest.mark.parametrize(
    "mutation",
    [
        "DELETE FROM chunks",
        "UPDATE results SET reason='fabricated' WHERE source_id=2",
        "UPDATE chunks SET decision='{}'",
    ],
)
def test_pass_when_chunk_evidence_damaged_then_reject_completed_reuse(
    tmp_path, mutation
):
    output = tmp_path / "pass.sqlite"
    with selector(tmp_path / "cache.sqlite") as cache:
        run_pass(items(2), cache, output, expected_count=2, **options())
        with sqlite3.connect(output) as db:
            db.execute(mutation)
        with pytest.raises(ValueError, match="evidence"):
            run_pass(items(2), cache, output, expected_count=2, **options())
