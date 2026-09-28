# this_file: tests/extract/test_legacy_fluent.py
"""OSS Fluent parsing delegates safely without altering source pairing policy."""

import importlib

import pytest


@pytest.fixture
def oss(monkeypatch):
    return importlib.import_module("vexy_localizzy.extract.oss")


def test_parser_when_consumer_imported_then_uses_shared_projection(oss):
    from vexy_localizzy.fluent_resources import flatten_pattern, parse_ftl

    assert oss.parse_ftl is parse_ftl
    assert oss.flatten_pattern is flatten_pattern


def test_pairing_when_target_adds_plural_variant_then_uses_source_default(
    tmp_path, oss
):
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "test.ftl").write_text(
        "items = { $n ->\n [one] One\n *[other] Other\n}\n"
    )
    (target / "test.ftl").write_text(
        "items = { $n ->\n [one] Jeden\n [few] Kilka\n *[other] Inne\n}\n"
    )
    assert list(oss.mozilla_units(target, source)) == [
        ("One", "Jeden", "items[one]", None, "test.ftl"),
        ("Other", "Kilka", "items[few]", None, "test.ftl"),
        ("Other", "Inne", "items", None, "test.ftl"),
    ]


def test_parser_when_junk_after_valid_message_then_refuse_partial_file(tmp_path, oss):
    path = tmp_path / "test.ftl"
    path.write_text("good = Fine\nbad = {\n")
    with pytest.raises(ValueError, match="Invalid Fluent"):
        oss.parse_mozilla_file(path)
