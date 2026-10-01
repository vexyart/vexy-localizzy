# this_file: tests/translate/test_json_sidecar.py
"""JSON file provenance state and Markdown QA used by ``translate_json_file``."""

import json
from pathlib import Path

import pytest

from vexy_localizzy.translate.json_checks import blocking, check, check_item
from vexy_localizzy.translate.json_sidecar import (
    assemble,
    clashing_keys,
    is_current,
    load_done,
    partial_path,
    read_json,
    sidecar,
    sidecar_path,
    source_hash,
    write_json,
)


def test_sidecar_path_when_target_named_then_siblings_with_new_suffix():
    out = Path("help/panel_pl.json")
    assert sidecar_path(out) == Path("help/panel_pl.localizzy.json"), (
        "sidecar sits next to the output"
    )
    assert partial_path(out) == Path("help/panel_pl.partial.json"), (
        "partial file sits next to the output"
    )


def test_source_hash_when_titles_then_key_takes_part():
    assert source_hash("A", "x", False) == source_hash("B", "x", False), "text only"
    assert source_hash("A", "x", True) != source_hash("B", "x", True), "title too"


def test_read_json_when_missing_or_not_object_then_empty_or_error(tmp_path):
    assert read_json(tmp_path / "missing.json") == {}, "a missing file is empty"
    (tmp_path / "list.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        read_json(tmp_path / "list.json")


def test_write_json_when_parent_missing_then_created_with_utf8(tmp_path):
    path = tmp_path / "a" / "b.json"
    write_json(path, {"zażółć": "ü"})
    assert "zażółć" in path.read_text(encoding="utf-8"), "non-ASCII kept as is"
    assert path.read_text(encoding="utf-8").endswith("}\n"), "trailing newline"


def test_load_done_when_sidecar_then_metadata_used_and_partial_merged(tmp_path):
    out = tmp_path / "o.json"
    write_json(out, {"a": "A-pl"})
    meta = {"sha256": "s", "model": "m", "state": "machine", "findings": []}
    write_json(sidecar_path(out), {"items": {"a": meta}})
    write_json(partial_path(out), {"b": {"text": "B-pl", "sha256": "t"}})
    done = load_done({"a": "A", "b": "B"}, out, titles=False)
    assert done["a"] == {"text": "A-pl"} | meta, done
    assert done["b"]["text"] == "B-pl", "partial items are read back"


def test_load_done_when_key_unknown_then_dropped(tmp_path):
    out = tmp_path / "o.json"
    write_json(out, {"gone": "x", "a": "A-pl"})
    done = load_done({"a": "A"}, out, titles=False)
    assert set(done) == {"a"} and done["a"]["state"] == "adopted", done


def test_is_current_when_text_changed_then_false():
    done = {"a": {"sha256": source_hash("a", "old", False)}}
    assert is_current(done, "a", "old", False), "unchanged English is current"
    assert not is_current(done, "a", "new", False), "changed English is stale"
    assert not is_current(done, "b", "old", False), "missing is not current"


def test_assemble_when_titles_collide_then_none():
    english = {"T1": "a", "T2": "b"}
    done = {
        k: {"title": "Same", "text": v, "sha256": source_hash(k, v, True)}
        for k, v in english.items()
    }
    assert assemble(english, done, titles=True) is None, "a lost key is incomplete"
    assert clashing_keys(done) == ["T1", "T2"], clashing_keys(done)


def test_assemble_when_complete_then_english_order():
    english = {"b": "B", "a": "A"}
    done = {
        k: {"text": v + "!", "sha256": source_hash(k, v, False)}
        for k, v in english.items()
    }
    assert list(assemble(english, done, titles=False).items()) == [
        ("b", "B!"),
        ("a", "A!"),
    ], "output follows English key order"


def test_sidecar_when_built_then_only_provenance_fields():
    done = {
        "a": {
            "text": "x",
            "sha256": "s",
            "model": "m",
            "state": "machine",
            "findings": [],
        }
    }
    doc = sidecar("help.json", "req-model", {"a": "A"}, done)
    assert doc == {
        "source": "help.json",
        "model": "req-model",
        "items": {
            "a": {"sha256": "s", "model": "m", "state": "machine", "findings": []}
        },
    }, doc


def test_check_when_link_target_or_code_count_changes_then_major():
    rules = {f["rule_id"] for f in check("See [a](x) `c`", "Zob. [a](y) c", "k")}
    assert {"MD-LINK", "MD-CODE"} <= rules, rules
    assert check("See [a](x)", "Zob. [a](x)", "k") == [], "a faithful copy is clean"


def test_check_item_when_title_empty_then_blocking():
    findings = check_item({"id": "T", "text": "a", "title": "T"}, {"text": "b"})
    assert blocking(findings) == ["T: TARGET-EMPTY"], findings


def test_blocking_when_only_minor_then_empty():
    minor = [{"unit_key": "k", "rule_id": "TARGET-UNCHANGED", "severity": "minor"}]
    assert blocking(minor) == [], "minor findings do not reject a batch"


def test_check_when_html_tag_dropped_then_tag_mismatch():
    findings = check("Press <b>OK</b>", "Naciśnij OK", "k")
    assert "TAG-MISMATCH" in {f["rule_id"] for f in findings}, json.dumps(findings)
