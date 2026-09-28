# this_file: tests/test_json_sequence.py
"""JSON sequence input accepts source strings containing physical newlines."""

from io import StringIO

from vexy_localizzy.json_sequence import values


def test_values_when_source_contains_physical_newline_then_preserves_record():
    records = list(values(StringIO('{"id":1,"text":"one\ntwo"}\n{"id":2}')))
    assert records == [{"id": 1, "text": "one\ntwo"}, {"id": 2}]
