# this_file: tests/test_source_extraction_paths.py
"""Extraction validates configuration and preserves aliased source files."""

import pytest

from vexy_localizzy.extract.single import extract


@pytest.mark.parametrize("alias", ["same", "symlink", "hardlink"])
def test_extract_when_output_aliases_input_then_preserve_original(tmp_path, alias):
    source = tmp_path / "catalog.po"
    raw = b'msgid "Open"\nmsgstr "Offen"\n'
    source.write_bytes(raw)
    out = source if alias == "same" else tmp_path / "out.tmx"
    if alias == "symlink":
        out.symlink_to(source)
    if alias == "hardlink":
        out.hardlink_to(source)
    with pytest.raises(ValueError, match="overwrite input"):
        extract(str(source), str(out), target_lang="de")
    assert source.read_bytes() == raw


def test_extract_when_output_aliases_reference_then_preserve_reference(tmp_path):
    source, target = tmp_path / "source.strings", tmp_path / "target.strings"
    source.write_text('"key"="Open";')
    target.write_text('"key"="Offen";')
    with pytest.raises(ValueError, match="overwrite input"):
        extract(str(target), str(source), source=str(source), target_lang="de")
    assert source.read_text() == '"key"="Open";'


@pytest.mark.parametrize(
    "suffix,kwargs",
    [(".po", {}), (".ftl", {"target_lang": "de"}), (".unknown", {"target_lang": "de"})],
)
def test_extract_when_configuration_incomplete_then_output_survives(
    tmp_path, suffix, kwargs
):
    source, out = tmp_path / ("input" + suffix), tmp_path / "out.tmx"
    source.write_text("")
    out.write_bytes(b"existing")
    with pytest.raises(ValueError):
        extract(str(source), str(out), **kwargs)
    assert out.read_bytes() == b"existing"
