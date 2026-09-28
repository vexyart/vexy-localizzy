# this_file: tests/test_export.py
"""TMX export must retain winning text, inline markup and original vote lineage."""

import json

import pytest
from lxml import etree

from vexy_localizzy.corpus.store import Corpus


def native(path, label, target="Księżyc"):
    path.write_text(
        f'<tmx><body><tu tuid="{label}"><tuv lang="en"><seg><hi>Moon</hi></seg></tuv><tuv lang="pl"><seg>{target}</seg></tuv></tu></body></tmx>'
    )
    return path


def test_export_when_reimported_then_keeps_original_votes_and_raw_references(tmp_path):
    output = tmp_path / "memory.tmx"
    with Corpus(tmp_path / "first.sqlite") as first:
        first.import_tmx(native(tmp_path / "a.tmx", "a"), family="alpha", weight=4)
        first.import_tmx(native(tmp_path / "b.tmx", "b"), family="beta", weight=3)
        first.import_tmx(
            native(tmp_path / "c.tmx", "c", "Luna"), family="gamma", weight=2
        )
        assert first.export_tmx(output) == 1
        original = first.provenance(first.winners()[0]["candidate_id"])
        first.import_tmx(output, family="derived", weight=99)
        assert first.winners()[0]["score"] == 7, (
            "Derived files must not create independent votes"
        )
        assert len(first.provenance(first.winners()[0]["candidate_id"])) == 2
    with Corpus(tmp_path / "second.sqlite") as second:
        second.import_tmx(output, family="derived", weight=99)
        winner = second.winners()[0]
        assert winner["target"] == "Księżyc" and winner["score"] == 7
        assert "<hi>Moon</hi>" in winner["source_xml"]
        refs = second.provenance(winner["candidate_id"])
        assert all(str(tmp_path / "second.sources") in r["snapshot"] for r in refs), (
            "New corpus must own its raw source snapshots"
        )
        assert {(r["path"], r["sha256"], r["ordinal"], r["family"]) for r in refs} == {
            (r["path"], r["sha256"], r["ordinal"], r["family"]) for r in original
        }


def test_export_when_broken_lineage_then_rejects_without_active_votes(tmp_path):
    output = tmp_path / "memory.tmx"
    with Corpus(tmp_path / "first.sqlite") as first:
        first.import_tmx(native(tmp_path / "a.tmx", "a"), family="alpha", weight=4)
        first.export_tmx(output)
    tree = etree.parse(output)
    tree.find(".//tu/prop").text = json.dumps([[999, 1, 1]])
    tree.write(output, encoding="utf-8")
    with Corpus(tmp_path / "second.sqlite") as second:
        with pytest.raises(ValueError, match="lineage"):
            second.import_tmx(output, family="derived", weight=1)
        assert second.winners() == []


def test_export_when_writer_fails_then_preserves_previous_file(tmp_path, monkeypatch):
    import vexy_localizzy.corpus.exporter as exporter

    output = tmp_path / "memory.tmx"
    output.write_text("previous")

    def fail(*args):
        raise OSError("simulated write failure")

    with Corpus(tmp_path / "first.sqlite") as first:
        first.import_tmx(native(tmp_path / "a.tmx", "a"), family="alpha", weight=4)
        monkeypatch.setattr(exporter, "make_unit", fail)
        with pytest.raises(OSError, match="simulated"):
            first.export_tmx(output)
    assert output.read_text() == "previous"


@pytest.mark.parametrize("change", ["ordinal", "target"])
def test_export_when_forged_reference_then_rejects(tmp_path, change):
    output = tmp_path / "memory.tmx"
    with Corpus(tmp_path / "first.sqlite") as first:
        first.import_tmx(native(tmp_path / "a.tmx", "a"), family="alpha", weight=4)
        first.export_tmx(output)
    tree = etree.parse(output)
    if change == "ordinal":
        refs = json.loads(tree.find(".//tu/prop").text)
        refs[0][1] = 999999
        tree.find(".//tu/prop").text = json.dumps(refs)
    else:
        tree.findall(".//tu/tuv")[1].find("seg").text = "INVENTED"
    tree.write(output, encoding="utf-8")
    with Corpus(tmp_path / "second.sqlite") as second:
        with pytest.raises(ValueError, match="lineage"):
            second.import_tmx(output, family="derived", weight=99)
        assert second.winners() == []


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", ".sources/overwrite.tmx"])
def test_export_when_database_or_snapshot_target_then_refuses(tmp_path, suffix):
    with Corpus(tmp_path / "first.sqlite") as corpus:
        target = (
            str(corpus.path) + suffix
            if ".sources" not in suffix
            else str(corpus.path.with_suffix(".sources") / "overwrite.tmx")
        )
        with pytest.raises(ValueError, match="destination"):
            corpus.export_tmx(target)
        assert corpus.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_export_when_namespaced_inline_then_roundtrip_is_valid(tmp_path):
    source = tmp_path / "namespaced.tmx"
    source.write_text(
        '<tmx xmlns="urn:tmx"><body><tu><tuv lang="en"><seg><hi>Moon</hi></seg></tuv><tuv lang="pl"><seg><hi>Księżyc</hi></seg></tuv></tu></body></tmx>'
    )
    output = tmp_path / "memory.tmx"
    with Corpus(tmp_path / "first.sqlite") as corpus:
        corpus.import_tmx(source, family="alpha", weight=4)
        corpus.export_tmx(output)
        assert etree.parse(output).find("header").get("o-tmf") == "vexy-localizzy"
    with Corpus(tmp_path / "second.sqlite") as corpus:
        corpus.import_tmx(output, family="derived", weight=99)
        assert corpus.winners()[0]["score"] == 4
