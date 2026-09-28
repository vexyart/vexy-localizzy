# this_file: tests/extract/test_legacy_mozilla.py
"""Mozilla consumers share parsing without inventing matches for ordinary keys."""

import importlib

import pytest


@pytest.fixture
def oss(monkeypatch):
    return importlib.import_module("vexy_localizzy.extract.oss")


@pytest.mark.parametrize(
    "suffix,text,expected",
    [
        ("dtd", '<!-- <!ENTITY hidden "No"> --><!ENTITY key "Yes">', {"key": "Yes"}),
        (
            "properties",
            "key=one\\nline\njoined=long\\\n  line\n",
            {"key": "one\nline", "joined": "longline"},
        ),
    ],
)
def test_mozilla_when_legacy_parser_would_misread_then_use_complete_values(
    tmp_path, oss, suffix, text, expected
):
    path = tmp_path / ("test." + suffix)
    path.write_text(text)
    assert oss.parse_mozilla_file(path) == expected


@pytest.mark.parametrize("content", [b'<!ENTITY good "Yes">\nbad', b"\xff"])
def test_dtd_when_invalid_then_refuse_resource(tmp_path, oss, content):
    path = tmp_path / "test.dtd"
    path.write_bytes(content)
    with pytest.raises(ValueError):
        oss.parse_mozilla_file(path)


def test_properties_when_key_looks_like_plural_then_do_not_guess_source(tmp_path, oss):
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "test.properties").write_text("key=Source\n")
    (target / "test.properties").write_text("key[one]=Target\n")
    assert list(oss.mozilla_units(target, source)) == [], (
        "Properties keys are literal, not Fluent selector variants"
    )


def test_mozilla_when_consumer_imported_then_uses_shared_parser(oss):
    from vexy_localizzy.extract.mozilla_resources import parse_mozilla

    assert oss.parse_mozilla is parse_mozilla
