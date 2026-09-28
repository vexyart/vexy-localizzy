# this_file: tests/test_snapshots.py
"""Accepted provenance remains resolvable after mutable inputs are replaced."""

import gzip
import hashlib

from vexy_localizzy.corpus.store import Corpus


def test_corpus_when_input_replaced_then_original_bytes_remain_recoverable(tmp_path):
    path = tmp_path / "raw.tmx"
    original = '<tmx><body><tu tuid="original-id"><prop type="x-provenance">a:42</prop><tuv lang="en_US"><seg>Cafe\u0301</seg></tuv><tuv lang="pl_PL"><seg>Kawa</seg></tuv></tu></body></tmx>'.encode()
    path.write_bytes(original)
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        report = corpus.import_tmx(path, family="alpha", weight=4)
        path.write_text("<tmx><body/></tmx>")
        corpus.import_tmx(path, family="alpha", weight=4)
        source = corpus.db.execute(
            "SELECT * FROM sources WHERE id=?", (report["source_id"],)
        ).fetchone()
        snapshot = source["snapshot"]
        assert (
            gzip.decompress(__import__("pathlib").Path(snapshot).read_bytes())
            == original
        )
        assert source["sha256"] == hashlib.sha256(original).hexdigest()


def test_corpus_when_parser_fails_then_stores_message_and_ordinal(tmp_path):
    import pytest

    path = tmp_path / "bad.tmx"
    path.write_text(
        "<tmx><body><tu><tuv><seg>Missing language</seg></tuv></tu></body></tmx>"
    )
    with Corpus(tmp_path / "memory.sqlite") as corpus:
        with pytest.raises(ValueError, match="language"):
            corpus.import_tmx(path, family="alpha", weight=4)
        row = corpus.db.execute("SELECT error,error_ordinal FROM sources").fetchone()
        assert "language" in row["error"] and row["error_ordinal"] == 1
