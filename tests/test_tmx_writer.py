# this_file: tests/test_tmx_writer.py
"""Generated TMX records retain literal values and publish only complete output."""

import xml.etree.ElementTree as ET

import pytest

from vexy_localizzy.memory.tmx_read import read_tmx
from vexy_localizzy.memory.tmx_write import TMXRecord, write_records


def test_writer_when_values_need_escaping_then_records_and_origins_survive(tmp_path):
    record = TMXRecord(
        'a"<&',
        (("en", "<b>A & B</b>"), ("pl", "Ą & <B>")),
        (("x-origin", "one<&"), ("x-origin", "two"), ("x-context", 'C"')),
    )
    output = tmp_path / "nested/out.tmx"
    assert write_records(output, iter([record]), source_lang="en") == 1
    root = ET.parse(output).getroot()
    assert root.find("body/tu").get("tuid") == record.key
    assert root.findtext("body/tu/tuv/seg") == "<b>A & B</b>"
    parsed = list(read_tmx(output))[0]
    assert parsed.properties == record.properties
    assert [s.text for s in parsed.segments] == [text for _, text in record.segments]
    assert not any(s.inline for s in parsed.segments)


def test_writer_when_generator_fails_then_existing_output_is_untouched(tmp_path):
    output = tmp_path / "out.tmx"
    output.write_bytes(b"existing")

    def records():
        yield TMXRecord("one", (("en", "One"),))
        raise RuntimeError("extraction failed")

    with pytest.raises(RuntimeError, match="extraction failed"):
        write_records(output, records(), source_lang="en")
    assert output.read_bytes() == b"existing"
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize(
    "record",
    [
        TMXRecord("x", ()),
        TMXRecord("x", (("en", "bad\x04text"),)),
        TMXRecord("x", (("not-a-language-???", "text"),)),
        TMXRecord("x", (("en", "ok"),), (("x-origin", "bad\x04origin"),)),
    ],
)
def test_writer_when_record_invalid_then_never_publish(tmp_path, record):
    output = tmp_path / "out.tmx"
    with pytest.raises(ValueError):
        write_records(output, [record], source_lang="en")
    assert not output.exists()


def test_writer_when_no_records_then_valid_empty_memory(tmp_path):
    output = tmp_path / "out.tmx"
    assert write_records(output, [], source_lang="en") == 0
    assert list(read_tmx(output)) == []
