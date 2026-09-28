# this_file: tests/test_export_identity.py
"""Source snapshots alone cannot identify corpus-local numeric entry IDs."""

import pytest

from vexy_localizzy.classification_inputs import prepare_inputs
from vexy_localizzy.corpus.store import Corpus


def test_export_when_rebuilt_in_different_order_then_refuse_stale_entry_ids(tmp_path):
    for name, text in (("a", "Open"), ("b", "Close")):
        (tmp_path / f"{name}.tmx").write_text(
            f'<tmx><body><tu><tuv lang="en"><seg>{text}</seg></tuv><tuv lang="de"><seg>{text}</seg></tuv></tu></body></tmx>'
        )
    metadata = []
    for index, order in enumerate(("ab", "ba")):
        with Corpus(tmp_path / f"{index}.sqlite") as corpus:
            for name in order:
                corpus.import_tmx(tmp_path / f"{name}.tmx", family=name, weight=1)
            metadata.append(prepare_inputs(corpus, tmp_path / f"{index}.jsonl"))
    assert metadata[0]["source_snapshot"] == metadata[1]["source_snapshot"]
    assert metadata[0]["entry_map_sha256"] != metadata[1]["entry_map_sha256"]
    with Corpus(tmp_path / "1.sqlite") as rebuilt:
        with pytest.raises(ValueError, match="entry map"):
            rebuilt.export_tmx(
                tmp_path / "out.tmx",
                entry_ids=[1],
                source_snapshot=metadata[0]["source_snapshot"],
                entry_map_sha256=metadata[0]["entry_map_sha256"],
            )
    assert not (tmp_path / "out.tmx").exists()


def test_export_when_snapshot_supplied_without_entry_map_then_refuse_ambiguous_ids(
    tmp_path,
):
    with Corpus(tmp_path / "empty.sqlite") as corpus:
        metadata = prepare_inputs(corpus, tmp_path / "inputs.jsonl")
        with pytest.raises(ValueError, match="entry map"):
            corpus.export_tmx(
                tmp_path / "out.tmx",
                entry_ids=[],
                source_snapshot=metadata["source_snapshot"],
            )


def test_export_when_inline_source_changes_with_same_text_then_entry_map_refuses(
    tmp_path,
):
    source = tmp_path / "inline.tmx"
    source.write_text(
        '<tmx><body><tu><tuv lang="en"><seg><hi>Open</hi></seg></tuv><tuv lang="de"><seg>Öffnen</seg></tuv></tu></body></tmx>'
    )
    with Corpus(tmp_path / "corpus.sqlite") as corpus:
        corpus.import_tmx(source, family="one", weight=1)
        metadata = prepare_inputs(corpus, tmp_path / "inputs.jsonl")
        with corpus.db:
            corpus.db.execute("UPDATE entries SET source_xml='<seg><b>Open</b></seg>'")
        with pytest.raises(ValueError, match="entry map"):
            corpus.export_tmx(
                tmp_path / "out.tmx",
                entry_ids=[1],
                source_snapshot=metadata["source_snapshot"],
                entry_map_sha256=metadata["entry_map_sha256"],
            )
    assert not (tmp_path / "out.tmx").exists()
