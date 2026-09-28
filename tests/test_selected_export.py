# this_file: tests/test_selected_export.py
"""Selected TMX exports preserve exact winners, source IDs and compact raw lineage."""

import hashlib
import json

import pytest
from lxml import etree

from vexy_localizzy.classification_inputs import prepare_inputs
from vexy_localizzy.corpus.exporter import DECISION_PROP, LINEAGE_PROP, MANIFEST_PROP
from vexy_localizzy.corpus.store import Corpus


def source(path, text, targets):
    root = etree.Element("tmx")
    unit = etree.SubElement(etree.SubElement(root, "body"), "tu")
    for locale, value in {"en": text, **targets}.items():
        etree.SubElement(etree.SubElement(unit, "tuv", lang=locale), "seg").text = value
    path.write_bytes(etree.tostring(root))
    return path


def populated(tmp_path):
    corpus = Corpus(tmp_path / "corpus.sqlite")
    corpus.import_tmx(
        source(tmp_path / "one.tmx", "Open", {"de": "Öffnen", "pl": "Otwórz"}),
        family="one",
        weight=4,
    )
    corpus.import_tmx(
        source(tmp_path / "two.tmx", "Open", {"de": "Öffnen"}), family="two", weight=3
    )
    corpus.import_tmx(
        source(tmp_path / "three.tmx", "Close", {"de": "Schließen"}),
        family="three",
        weight=2,
    )
    corpus.import_tmx(
        source(tmp_path / "losing.tmx", "Open", {"de": "Aufmachen"}),
        family="losing",
        weight=1,
    )
    return corpus


def test_export_when_selected_then_all_targets_weights_and_only_used_origins(tmp_path):
    output = tmp_path / "selected.tmx"
    with populated(tmp_path) as corpus:
        key = corpus.db.execute(
            "SELECT id FROM entries WHERE source='Open'"
        ).fetchone()[0]
        metadata = prepare_inputs(corpus, tmp_path / "inputs.jsonl")
        assert (
            corpus.export_tmx(
                output,
                entry_ids=iter([key]),
                source_snapshot=metadata["source_snapshot"],
                entry_map_sha256=metadata["entry_map_sha256"],
            )
            == 2
        )
        expected = {
            row["candidate_id"]: row
            for row in corpus.winners()
            if row["entry_id"] == key
        }
    tree = etree.parse(output)
    units = tree.findall(".//tu")
    assert len(units) == 2
    for unit in units:
        assert [child.tag for child in unit] == [
            "prop",
            "prop",
            "prop",
            "tuv",
            "tuv",
        ], "TMX properties must precede all language variants"
        row = expected[int(unit.get("tuid"))]
        assert unit.findtext("prop[@type='x-vexy-localizzy-source-id']") == str(key)
        assert (
            json.loads(unit.findtext(f"prop[@type='{DECISION_PROP}']"))["score"]
            == row["score"]
        )
        assert json.loads(unit.findtext(f"prop[@type='{LINEAGE_PROP}']"))
    registry = json.loads(tree.findtext(f"header/prop[@type='{MANIFEST_PROP}']"))
    assert {row["name"] for row in registry["families"].values()} == {"one", "two"}
    assert len(registry["origins"]) == 2
    selection = json.loads(
        tree.findtext("header/prop[@type='x-vexy-localizzy-selection']")
    )
    assert (
        selection["entries"] == 1
        and selection["source_snapshot"] == metadata["source_snapshot"]
    )
    assert (
        selection["entry_ids_sha256"] == hashlib.sha256(f"{key}\n".encode()).hexdigest()
    )
    with Corpus(tmp_path / "restored.sqlite") as restored:
        restored.import_tmx(output, family="derived", weight=99)
        assert {
            (row["source"], row["locale"], row["target"], row["score"])
            for row in restored.winners()
        } == {
            (row["source"], row["locale"], row["target"], row["score"])
            for row in expected.values()
        }
        assert all(
            ref["family"] != "three"
            for row in restored.winners()
            for ref in restored.provenance(row["candidate_id"])
        )


@pytest.mark.parametrize("ids", [[999], [1, 1], [True], [0], ["1"], [2**63]])
def test_export_when_selected_ids_invalid_then_preserve_output_and_clean_staging(
    tmp_path, ids
):
    output = tmp_path / "selected.tmx"
    output.write_text("previous")
    with populated(tmp_path) as corpus:
        with pytest.raises(ValueError):
            corpus.export_tmx(output, entry_ids=ids)
        assert output.read_text() == "previous"
        assert not corpus.db.in_transaction
        assert "export_selection" not in [
            row[1] for row in corpus.db.execute("PRAGMA database_list")
        ]
    assert list(tmp_path.glob(".localizzy-export-*")) == []


def test_export_when_empty_selection_then_empty_memory_not_all_entries(tmp_path):
    with populated(tmp_path) as corpus:
        assert corpus.export_tmx(tmp_path / "empty.tmx", entry_ids=[]) == 0
    tree = etree.parse(tmp_path / "empty.tmx")
    assert tree.findall(".//tu") == []
    registry = json.loads(tree.findtext(f"header/prop[@type='{MANIFEST_PROP}']"))
    assert registry["origins"] == registry["families"] == {}


def test_export_when_snapshot_changed_then_refuse_stale_selection(tmp_path):
    output = tmp_path / "selected.tmx"
    with populated(tmp_path) as corpus:
        metadata = prepare_inputs(corpus, tmp_path / "inputs.jsonl")
        corpus.deactivate(tmp_path / "three.tmx")
        with pytest.raises(ValueError, match="snapshot"):
            corpus.export_tmx(
                output,
                entry_ids=[1],
                source_snapshot=metadata["source_snapshot"],
                entry_map_sha256=metadata["entry_map_sha256"],
            )
    assert not output.exists()


def test_export_when_source_inactive_then_cannot_satisfy_selected_id(tmp_path):
    with populated(tmp_path) as corpus:
        key = corpus.db.execute(
            "SELECT id FROM entries WHERE source='Close'"
        ).fetchone()[0]
        corpus.deactivate(tmp_path / "three.tmx")
        with pytest.raises(ValueError, match="winner"):
            corpus.export_tmx(tmp_path / "selected.tmx", entry_ids=[key])


def test_export_when_sources_change_during_iteration_then_consistent_snapshot(tmp_path):
    output = tmp_path / "selected.tmx"
    with populated(tmp_path) as corpus:
        metadata = prepare_inputs(corpus, tmp_path / "inputs.jsonl")

        def ids():
            with Corpus(corpus.path) as writer:
                writer.deactivate(tmp_path / "one.tmx")
            yield 1

        assert (
            corpus.export_tmx(
                output,
                entry_ids=ids(),
                source_snapshot=metadata["source_snapshot"],
                entry_map_sha256=metadata["entry_map_sha256"],
            )
            == 2
        )
        assert len([row for row in corpus.winners() if row["source"] == "Open"]) == 1
    tree = etree.parse(output)
    assert sorted(
        json.loads(node.text)["score"]
        for node in tree.findall(f".//tu/prop[@type='{DECISION_PROP}']")
    ) == [4, 7]


def test_export_when_selected_input_raises_then_previous_output_survives(tmp_path):
    output = tmp_path / "selected.tmx"
    output.write_text("previous")

    def ids():
        yield 1
        raise RuntimeError("interrupted input")

    with populated(tmp_path) as corpus:
        with pytest.raises(RuntimeError, match="interrupted"):
            corpus.export_tmx(output, entry_ids=ids())
        assert not corpus.db.in_transaction
        assert "export_selection" not in [
            row[1] for row in corpus.db.execute("PRAGMA database_list")
        ]
    assert output.read_text() == "previous"
    assert list(tmp_path.glob(".localizzy-export-*")) == []
