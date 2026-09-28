# this_file: tests/test_corpus.py
"""Weighted source voting and interrupted import contracts."""

import sqlite3

import pytest

from vexy_localizzy.corpus import Corpus


def memory(path, targets, source="Moon"):
    path.write_text(
        '<tmx><header srclang="en"/><body>'
        + "".join(
            f'<tu><tuv lang="en"><seg>{source}</seg></tuv><tuv lang="pl"><seg>{target}</seg></tuv></tu>'
            for target in targets
        )
        + "</body></tmx>"
    )
    return path


def test_corpus_when_repeated_source_then_does_not_multiply_votes(tmp_path):
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        corpus.import_tmx(
            memory(tmp_path / "a.tmx", ["A"] * 5), family="alpha", weight=4
        )
        corpus.import_tmx(memory(tmp_path / "b.tmx", ["B"]), family="beta", weight=3)
        corpus.import_tmx(
            memory(tmp_path / "c.tmx", ["B", "B"]), family="gamma", weight=2
        )
        winner = corpus.winners()[0]
        assert winner["target"] == "B" and winner["score"] == 5
        assert len(corpus.provenance(winner["candidate_id"])) == 3


def test_corpus_when_same_bytes_different_family_then_rejects_double_credit(tmp_path):
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        a = memory(tmp_path / "a.tmx", ["A"])
        corpus.import_tmx(a, family="alpha", weight=4)
        b = tmp_path / "b.tmx"
        b.write_bytes(a.read_bytes())
        with pytest.raises(ValueError, match="family"):
            corpus.import_tmx(b, family="beta", weight=3)


def test_corpus_when_reimported_then_counts_and_scores_are_stable(tmp_path):
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        path = memory(tmp_path / "a.tmx", ["A", "A"])
        first = corpus.import_tmx(path, family="alpha", weight=4)
        again = corpus.import_tmx(path, family="alpha", weight=4)
        assert again["cached"] and first["units"] == again["units"] == 2
        assert corpus.winners()[0]["score"] == 4


def test_corpus_when_source_replaced_or_removed_then_old_votes_retracted(tmp_path):
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        path = memory(tmp_path / "a.tmx", ["A"])
        corpus.import_tmx(path, family="alpha", weight=4)
        memory(path, ["B"])
        corpus.import_tmx(path, family="alpha", weight=4)
        assert [x["target"] for x in corpus.winners()] == ["B"]
        corpus.deactivate(path)
        assert corpus.winners() == []


def test_corpus_when_failed_import_then_partial_rows_do_not_vote(tmp_path):
    with Corpus(tmp_path / "memory.sqlite", batch_size=1) as corpus:
        path = memory(tmp_path / "a.tmx", ["A"])
        corpus.import_tmx(path, family="alpha", weight=4)
        path.write_text(
            '<tmx><body><tu><tuv lang="en"><seg>Moon</seg></tuv><tuv lang="pl"><seg>B</seg></tuv></tu><tu>'
            + " " * 100000
        )
        with pytest.raises(Exception):
            corpus.import_tmx(path, family="alpha", weight=4)
        assert corpus.winners()[0]["target"] == "A", (
            "Last successful source remains active after failed replacement"
        )


def test_corpus_when_tied_then_stable_target_and_tie_flag(tmp_path):
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        corpus.import_tmx(memory(tmp_path / "z.tmx", ["Z"]), family="z", weight=3)
        corpus.import_tmx(memory(tmp_path / "a.tmx", ["A"]), family="a", weight=3)
        winner = corpus.winners()[0]
        assert winner["target"] == "A" and winner["tied"]


def test_corpus_when_invalid_weight_then_rejects(tmp_path):
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        with pytest.raises(ValueError):
            corpus.import_tmx(
                memory(tmp_path / "a.tmx", ["A"]), family="alpha", weight=0
            )


def test_corpus_when_existing_unknown_database_then_does_not_adopt(tmp_path):
    path = tmp_path / "other.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises(ValueError, match="schema"):
        Corpus(path)


def test_corpus_when_prior_bytes_restored_then_reactivates_that_snapshot(tmp_path):
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        path = memory(tmp_path / "a.tmx", ["A"])
        original = path.read_bytes()
        corpus.import_tmx(path, family="alpha", weight=4)
        memory(path, ["B"])
        corpus.import_tmx(path, family="alpha", weight=4)
        path.write_bytes(original)
        restored = corpus.import_tmx(path, family="alpha", weight=4)
        assert restored["cached"] and corpus.winners()[0]["target"] == "A"


def test_corpus_when_deactivated_then_explicit_reimport_reactivates(tmp_path):
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        path = memory(tmp_path / "a.tmx", ["A"])
        corpus.import_tmx(path, family="alpha", weight=4)
        corpus.deactivate(path)
        corpus.import_tmx(path, family="alpha", weight=4)
        assert len(corpus.winners()) == 1


def test_corpus_when_no_target_then_exclusion_is_visible_on_cached_run(tmp_path):
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        path = tmp_path / "no-target.tmx"
        path.write_text(
            '<tmx><body><tu><tuv lang="en"><seg>Moon</seg></tuv></tu></body></tmx>'
        )
        first = corpus.import_tmx(path, family="alpha", weight=4)
        again = corpus.import_tmx(path, family="alpha", weight=4)
        assert first["excluded"] == again["excluded"] == 1
        assert not corpus.winners()


def test_corpus_when_source_changes_mid_import_then_invalidates_committed_prefix(
    tmp_path, monkeypatch
):
    import vexy_localizzy.importer as importer

    path = memory(tmp_path / "changing.tmx", ["ORIGINAL"])
    original = path.read_bytes()
    read = importer.read_tmx

    def changed_read(source):
        memory(path, ["CHANGED"])
        yield from read(source)

    with Corpus(tmp_path / "memory.sqlite", batch_size=1) as corpus:
        monkeypatch.setattr(importer, "read_tmx", changed_read)
        with pytest.raises(ValueError, match="changed"):
            corpus.import_tmx(path, family="alpha", weight=4)
        monkeypatch.setattr(importer, "read_tmx", read)
        path.write_bytes(original)
        corpus.import_tmx(path, family="alpha", weight=4)
        assert corpus.winners()[0]["target"] == "ORIGINAL", (
            "A checkpoint with invalid source identity must never resume"
        )
