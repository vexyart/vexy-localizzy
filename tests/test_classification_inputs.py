# this_file: tests/test_classification_inputs.py
"""Classification inputs include only complete active source coverage."""

import json

import pytest

from vexy_localizzy.classification_inputs import prepare_inputs
from vexy_localizzy.corpus.store import Corpus


def test_inputs_when_source_inactive_then_excludes_its_text_and_coverage(tmp_path):
    with Corpus(tmp_path / "corpus.sqlite") as corpus:
        for name, locale in [("a", "pl"), ("b", "cy")]:
            path = tmp_path / f"{name}.tmx"
            path.write_text(
                f'<tmx><body><tu><tuv lang="en"><seg>Moon {name}</seg></tuv><tuv lang="{locale}"><seg>Target</seg></tuv></tu></body></tmx>'
            )
            corpus.import_tmx(path, family=name, weight=1)
        corpus.deactivate(tmp_path / "b.tmx")
        output = tmp_path / "inputs.jsonl"
        metadata = prepare_inputs(corpus, output, expected_sources=1)
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        assert metadata["coverage"] == {"pl": 1} and metadata["entries"] == 1
        assert rows[1]["text"] == "Moon a" and rows[1]["locales"] == ["pl"]
        with pytest.raises(ValueError, match="destination"):
            prepare_inputs(corpus, corpus.path, expected_sources=1)
        with pytest.raises(ValueError, match="source count"):
            prepare_inputs(corpus, output, expected_sources=2)
        assert [json.loads(line) for line in output.read_text().splitlines()] == rows
