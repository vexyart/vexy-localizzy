# this_file: tests/editorial/test_editorial_json.py
"""Keyed and titled JSON files: reviewer units, staleness, pairing and file mode."""

import json
import stat

import pytest
from editorial_fixtures import candidate, run_json, write_json

from vexy_localizzy.editorial.json_files import json_units


def test_apply_json_when_title_counts_differ_then_refused_and_file_untouched(tmp_path):
    en = write_json(tmp_path / "en.json", {"A": "a", "B": "b"})
    pl = write_json(tmp_path / "pl.json", {"PA": "pa", "PB": "pb", "PC": "pc"})
    before = pl.read_bytes()
    change = candidate("B", "B\n\nb", "PB\n\npb", "PB2\n\npb2")
    with pytest.raises(ValueError, match="cannot be paired"):
        run_json(pl, en, [change], "pl", dry_run=False)
    assert pl.read_bytes() == before, "a refused file is not rewritten"


def test_apply_json_when_revised_title_collides_with_later_title_then_refused(tmp_path):
    en = write_json(tmp_path / "en.json", {"A": "a", "B": "b"})
    pl = write_json(tmp_path / "pl.json", {"PA": "pa", "PB": "pb"})
    before = pl.read_bytes()
    change = candidate("A", "A\n\na", "PA\n\npa", "PB\n\npa")
    with pytest.raises(ValueError, match="collide"):
        run_json(pl, en, [change], "pl", dry_run=False)
    assert pl.read_bytes() == before, "a refused file is not rewritten"


def test_apply_json_when_title_revised_then_title_and_text_rewritten_in_order(tmp_path):
    en = write_json(tmp_path / "en.json", {"A": "a", "B": "b"})
    pl = write_json(tmp_path / "pl.json", {"PA": "pa", "PB": "pb"})
    change = candidate("A", "A\n\na", "PA\n\npa", "PA2\n\npa2")
    outcome = run_json(pl, en, [change], "pl", dry_run=False)
    assert len(outcome.applied) == 1, outcome
    assert list(json.loads(pl.read_text("utf-8")).items()) == [
        ("PA2", "pa2"),
        ("PB", "pb"),
    ], "order and the untouched entry are kept"


def test_apply_json_when_title_revision_lacks_separator_then_skipped_as_format(
    tmp_path,
):
    en = write_json(tmp_path / "en.json", {"A": "a"})
    pl = write_json(tmp_path / "pl.json", {"PA": "pa"})
    change = candidate("A", "A\n\na", "PA\n\npa", "PA2 pa2")
    outcome = run_json(pl, en, [change], "pl", dry_run=False)
    assert [s["reason"] for s in outcome.skipped] == ["format"], outcome


def test_apply_json_when_keyed_target_changed_then_stale(tmp_path):
    en = write_json(tmp_path / "en.json", {"k": "Text"})
    pl = write_json(tmp_path / "pl.json", {"k": "Tekst (human)"})
    change = candidate("k", "Text", "Tekst", "Tekst poprawiony")
    outcome = run_json(pl, en, [change], "pl", dry_run=False)
    assert outcome.applied == [], outcome
    assert outcome.stale[0]["reason"] == "translation changed", outcome.stale


def test_apply_json_when_applied_then_file_mode_kept(tmp_path):
    en = write_json(tmp_path / "en.json", {"k": "Text"})
    pl = write_json(tmp_path / "pl.json", {"k": "Tekst"})
    pl.chmod(0o644)
    change = candidate("k", "Text", "Tekst", "Tekst poprawiony")
    outcome = run_json(pl, en, [change], "pl", dry_run=False)
    assert len(outcome.applied) == 1, outcome
    assert json.loads(pl.read_text(encoding="utf-8")) == {"k": "Tekst poprawiony"}, (
        "the correction is written"
    )
    assert stat.S_IMODE(pl.stat().st_mode) == 0o644, "atomic write keeps the mode"


def test_json_units_when_keyed_then_string_values_only(tmp_path):
    en = write_json(tmp_path / "en.json", {"a": "Alpha", "b": {"nested": 1}, "c": "C"})
    pl = write_json(tmp_path / "pl.json", {"a": "Alfa", "b": {"nested": 1}})
    found = json_units(en, pl)
    assert [(u.key, u.source, u.target) for u in found] == [("a", "Alpha", "Alfa")], (
        "non-string and untranslated values are left out"
    )


def test_json_units_when_titled_then_paired_by_position(tmp_path):
    en = write_json(tmp_path / "en.json", {"A": "a", "B": "b"})
    pl = write_json(tmp_path / "pl.json", {"PA": "pa", "PB": "pb"})
    found = json_units(en, pl)
    assert [(u.source, u.target) for u in found] == [
        ("A\n\na", "PA\n\npa"),
        ("B\n\nb", "PB\n\npb"),
    ], "title and text are one message"


def test_json_units_when_titled_lengths_differ_then_refused(tmp_path):
    en = write_json(tmp_path / "en.json", {"A": "a"})
    pl = write_json(tmp_path / "pl.json", {"PA": "pa", "PB": "pb"})
    with pytest.raises(ValueError, match="cannot pair"):
        json_units(en, pl)


def test_json_units_when_top_level_not_object_then_refused(tmp_path):
    en = write_json(tmp_path / "en.json", ["a"])
    pl = write_json(tmp_path / "pl.json", {"a": "b"})
    with pytest.raises(ValueError, match="JSON object"):
        json_units(en, pl)
