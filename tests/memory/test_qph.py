# this_file: tests/memory/test_qph.py
"""Phrase book export keeps literal translations and translator context."""

from pathlib import Path

import pytest
from lxml import etree

from vexy_localizzy.cli.tm import TM_COMMANDS
from vexy_localizzy.memory.qph import tmx2qph


def memory(tmp_path: Path, units: str) -> Path:
    path = tmp_path / "input.tmx"
    path.write_text(
        f'<tmx version="1.4"><header srclang="en"/><body>{units}</body></tmx>'
    )
    return path


def test_export_preserves_text_notes_status_and_order(tmp_path):
    source = memory(
        tmp_path,
        """
    <tu><prop type="x-status">proposed</prop><note>Definition.</note>
      <tuv xml:lang="en"><seg>  A &amp; &lt;B&gt;\nC  </seg></tuv>
      <tuv xml:lang="es-419"><note>Translator note.</note><seg>  Á &amp; B\nC  </seg></tuv></tu>
    <tu><tuv xml:lang="en"><seg>Brand</seg></tuv>
      <tuv xml:lang="es-419"><seg>Brand</seg></tuv></tu>
    """,
    )
    out = tmp_path / "nested" / "book.qph"
    result = TM_COMMANDS["tmx2qph"](str(source), str(out), "es-419")
    root = etree.parse(out).getroot()
    assert result["phrases"] == 2
    assert root.attrib == {"language": "es_419", "sourcelanguage": "en"}
    assert root[0].findtext("source") == "  A & <B>\nC  "
    assert root[0].findtext("target") == "  Á & B\nC  "
    assert (
        root[0].findtext("definition")
        == "Status: proposed\n\nDefinition.\n\nTranslator note."
    )
    assert root[1].findtext("target") == "Brand"
    assert etree.parse(out).docinfo.doctype == "<!DOCTYPE QPH>"
    first = out.read_bytes()
    tmx2qph(str(source), str(out), "es-419")
    assert out.read_bytes() == first, "Export must be deterministic"


@pytest.mark.parametrize(
    "units, error",
    [
        ('<tu><tuv xml:lang="en"><seg>A</seg></tuv></tu>', "Expected one de"),
        (
            '<tu><tuv xml:lang="en"><seg>A</seg></tuv><tuv xml:lang="de"><seg/></tuv></tu>',
            "Empty",
        ),
        (
            '<tu><tuv xml:lang="en"><seg>A<b>B</b></seg></tuv><tuv xml:lang="de"><seg>C</seg></tuv></tu>',
            "Inline",
        ),
        (
            '<tu><tuv xml:lang="en"><seg>A</seg></tuv><tuv xml:lang="de"><seg>B</seg></tuv><tuv xml:lang="de"><seg>C</seg></tuv></tu>',
            "Expected one de",
        ),
        ("", "No translation units"),
        ("<tu>", None),
    ],
)
def test_invalid_input_preserves_existing_output(tmp_path, units, error):
    source = memory(tmp_path, units)
    out = tmp_path / "book.qph"
    out.write_bytes(b"existing")
    with pytest.raises((ValueError, etree.XMLSyntaxError), match=error):
        tmx2qph(str(source), str(out), "de")
    assert out.read_bytes() == b"existing"


def test_rejects_overwriting_input(tmp_path):
    source = memory(tmp_path, "")
    before = source.read_bytes()
    with pytest.raises(ValueError, match="different"):
        tmx2qph(str(source), str(source), "de")
    assert source.read_bytes() == before


def test_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        tmx2qph(str(tmp_path / "missing.tmx"), str(tmp_path / "out.qph"), "de")
