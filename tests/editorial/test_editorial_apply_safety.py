# this_file: tests/editorial/test_editorial_apply_safety.py
"""Applying without loss: ledger reruns, all-or-nothing writes, variants, overwrites."""

import json

import pytest
from editorial_fixtures import candidate, ts, units, write_candidates, write_json

from vexy_localizzy.editorial import commit
from vexy_localizzy.editorial.apply import apply_review

OPEN = "<source>Open</source><translation>Ouvrir</translation>"
SAVE = "<source>Save</source><translation>Enregistrer</translation>"
VARIANT_PLURAL = (
    '<source>%n file(s)</source><translation><numerusform variants="yes">'
    "<lengthvariant>%n fichier</lengthvariant><lengthvariant>%n f.</lengthvariant>"
    "</numerusform><numerusform>%n fichiers</numerusform></translation>"
)
VARIANT_SCALAR = (
    '<source>Long label</source><translation variants="yes">'
    "<lengthvariant>Libellé long</lengthvariant><lengthvariant>Court</lengthvariant>"
    "</translation>"
)


def _catalog(tmp_path, *messages):
    path = tmp_path / "cat.ts"
    text = ts(list(messages)).replace(
        "<message><source>%n", '<message numerus="yes"><source>%n'
    )
    path.write_text(text, encoding="utf-8")
    return path


def _open_fix(tmp_path):
    return write_candidates(
        tmp_path / "c.jsonl", [candidate("Main.open", "Open", "Ouvrir", "Ouvrez")]
    )


def _staged(tmp_path) -> list[str]:
    return [p.name for p in tmp_path.rglob("*.staged")]


def test_apply_review_when_ledger_exists_then_refused_and_catalog_untouched(tmp_path):
    catalog, path = _catalog(tmp_path, OPEN), _open_fix(tmp_path)
    ledger = tmp_path / "ledger.json"
    ledger.write_text('{"changes": ["first run"]}', encoding="utf-8")
    before = catalog.read_bytes()
    with pytest.raises(ValueError, match="--force"):
        apply_review(catalog, "fr", path, ledger)
    assert catalog.read_bytes() == before, "nothing applied without --force"
    assert "first run" in ledger.read_text("utf-8"), "the earlier record survives"


def test_apply_review_when_rerun_with_force_then_already_applied_not_stale(tmp_path):
    catalog, path = _catalog(tmp_path, OPEN), _open_fix(tmp_path)
    ledger = tmp_path / "ledger.json"
    assert apply_review(catalog, "fr", path, ledger)["applied"] == 1, "first run"
    summary = apply_review(catalog, "fr", path, ledger, force=True)
    assert summary["applied"] == 0, summary
    assert summary["skipped"]["already_applied"] == 1, summary["skipped"]
    assert summary["skipped"]["stale"] == 0, "a landed correction is not stale"


def test_apply_review_when_json_rerun_then_already_applied(tmp_path):
    en = write_json(tmp_path / "en.json", {"k": "Text"})
    pl = write_json(tmp_path / "pl.json", {"k": "Tekst"})
    path = write_candidates(
        tmp_path / "c.jsonl", [candidate("k", "Text", "Tekst", "Tekst nowy")]
    )
    ledger = tmp_path / "l.json"
    apply_review(pl, "pl", path, ledger, source_json=en)
    summary = apply_review(pl, "pl", path, ledger, source_json=en, force=True)
    assert summary["skipped"]["already_applied"] == 1, summary["skipped"]


def test_apply_review_when_ledger_dir_unwritable_then_catalog_untouched(tmp_path):
    catalog, path = _catalog(tmp_path, OPEN), _open_fix(tmp_path)
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x", encoding="utf-8")
    before = catalog.read_bytes()
    with pytest.raises(OSError):
        apply_review(catalog, "fr", path, blocker / "ledger.json")
    assert catalog.read_bytes() == before, "no catalog change without a ledger"
    assert _staged(tmp_path) == [], "staged files are removed"


def test_apply_review_when_ledger_replace_fails_then_catalog_restored(
    tmp_path, monkeypatch
):
    catalog, path = _catalog(tmp_path, OPEN), _open_fix(tmp_path)
    ledger = tmp_path / "ledger.json"
    before = catalog.read_bytes()
    real_replace = commit.os.replace

    def replace(source, dest):
        if str(dest).endswith("ledger.json"):
            raise OSError("disk full")
        real_replace(source, dest)

    monkeypatch.setattr(commit.os, "replace", replace)
    with pytest.raises(OSError, match="disk full"):
        apply_review(catalog, "fr", path, ledger)
    assert catalog.read_bytes() == before, "the catalog gets its bytes back"
    assert not ledger.exists() and _staged(tmp_path) == [], "nothing left behind"


def test_apply_review_when_catalog_mode_set_then_kept(tmp_path):
    catalog, path = _catalog(tmp_path, OPEN), _open_fix(tmp_path)
    catalog.chmod(0o640)
    apply_review(catalog, "fr", path, tmp_path / "ledger.json")
    assert catalog.stat().st_mode & 0o777 == 0o640, oct(catalog.stat().st_mode)


@pytest.mark.parametrize("message", [VARIANT_PLURAL, VARIANT_SCALAR])
def test_apply_review_when_message_has_length_variants_then_skipped_and_run_continues(
    tmp_path, message
):
    catalog = _catalog(tmp_path, message, SAVE)
    keys = list(units(catalog))
    live = units(catalog)[keys[0]]
    # A candidate for a variant message carries its first variant as the text.
    before = (
        [live.plural.forms["0"], live.plural.forms["1"]]
        if live.plural
        else live.variants[0]
    )
    revised = ["%n fich.", "%n fichiers"] if live.plural else "Libellé"
    path = write_candidates(
        tmp_path / "c.jsonl",
        [
            candidate(keys[0], live.source, before, revised),
            candidate(keys[1], "Save", "Enregistrer", "Sauvegarder"),
        ],
    )
    summary = apply_review(catalog, "fr", path, tmp_path / "ledger.json")
    assert summary["applied"] == 1, summary
    assert summary["skipped_ids"].get("variants") == [keys[0]], summary
    assert units(catalog)[keys[1]].target == "Sauvegarder", "the other fix lands"
    after = units(catalog)[keys[0]]
    assert (after.variants, after.plural) == (live.variants, live.plural), (
        "the variant message is untouched"
    )


@pytest.mark.parametrize(
    ("ledger_name", "candidates_name"),
    [("cat.ts", "c.jsonl"), ("c.jsonl", "c.jsonl"), ("l.json", "cat.ts")],
)
def test_apply_review_when_output_is_an_input_then_refused(
    tmp_path, ledger_name, candidates_name
):
    catalog = _catalog(tmp_path, OPEN)
    _open_fix(tmp_path)
    before = catalog.read_bytes()
    with pytest.raises(ValueError, match="same file"):
        apply_review(
            catalog,
            "fr",
            tmp_path / candidates_name,
            tmp_path / "." / ledger_name,
            force=True,
        )
    assert catalog.read_bytes() == before, "nothing overwritten"


def test_apply_review_when_ledger_is_source_json_then_refused(tmp_path):
    en = write_json(tmp_path / "en.json", {"k": "Text"})
    pl = write_json(tmp_path / "pl.json", {"k": "Tekst"})
    path = write_candidates(tmp_path / "c.jsonl", [])
    with pytest.raises(ValueError, match="source JSON"):
        apply_review(pl, "pl", path, en, source_json=en, force=True)
    assert json.loads(en.read_text("utf-8")) == {"k": "Text"}, "English kept"
