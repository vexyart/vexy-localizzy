# this_file: tests/editorial/test_editorial_apply.py
"""Applying review candidates to TS catalogs: staleness, state, skips and the ledger."""

import json

import pytest
from editorial_fixtures import candidate, run_ts, ts, units, write_candidates

from vexy_localizzy.editorial.apply import SKIP_REASONS, apply_review
from vexy_localizzy.editorial.candidate_file import load_candidates

ALL_SEVERITIES = {"critical", "major", "minor"}
ALL_FAMILIES = {"accuracy", "markup"}


def _catalog(tmp_path, *messages):
    path = tmp_path / "cat.ts"
    path.write_text(ts(list(messages)), encoding="utf-8")
    return path


def test_apply_ts_when_key_now_names_another_source_then_stale_and_unchanged(tmp_path):
    # Review saw "Open" at Main.open; an upgrade removed it and "Open…" took the key.
    catalog = _catalog(
        tmp_path, "<source>Open…</source><translation>Ouvrir…</translation>"
    )
    change = candidate("Main.open", "Open", "Ouvrir", "Ouvrir le fichier")
    outcome = run_ts(catalog, [change], "fr", dry_run=False)
    assert outcome.applied == [], "a correction for another source must not land"
    assert outcome.stale[0]["reason"] == "source changed", outcome.stale
    assert outcome.stale[0]["live_source"] == "Open…", outcome.stale
    assert units(catalog)["Main.open"].target == "Ouvrir…", "catalog untouched"


def test_apply_ts_when_human_edited_after_review_then_stale_and_kept(tmp_path):
    catalog = _catalog(
        tmp_path, "<source>Open</source><translation>Ouvrir (humain)</translation>"
    )
    change = candidate("Main.open", "Open", "Ouvrir", "Ouvrir le fichier")
    outcome = run_ts(catalog, [change], "fr", dry_run=False)
    assert outcome.applied == [], "a human edit wins"
    assert outcome.stale[0]["reason"] == "translation changed", outcome.stale
    assert outcome.stale[0]["live_target"] == "Ouvrir (humain)", outcome.stale
    assert units(catalog)["Main.open"].target == "Ouvrir (humain)", "kept"


def test_apply_ts_when_key_missing_then_listed_as_stale(tmp_path):
    catalog = _catalog(
        tmp_path, "<source>Open</source><translation>Ouvrir</translation>"
    )
    change = candidate("Main.gone", "Gone", "Parti", "Disparu")
    outcome = run_ts(catalog, [change], "fr", dry_run=True)
    assert outcome.applied == [], "nothing to apply"
    assert outcome.stale[0]["reason"] == "message missing", outcome.stale


def test_apply_ts_when_unit_unfinished_then_state_kept_unless_finish(tmp_path):
    catalog = _catalog(
        tmp_path,
        '<source>Draft</source><translation type="unfinished">Brouilon</translation>',
    )
    change = candidate("Main.draft", "Draft", "Brouilon", "Brouillon")
    applied = run_ts(catalog, [change], "fr", dry_run=False).applied
    assert units(catalog)["Main.draft"].target == "Brouillon", "text applied"
    assert units(catalog)["Main.draft"].state == "untranslated", "stays unfinished"
    assert 'type="unfinished"' in catalog.read_text(encoding="utf-8"), "XML state kept"
    assert applied[0]["state_before"] == applied[0]["state_after"] == "untranslated", (
        "the ledger records the kept state"
    )

    change = candidate("Main.draft", "Draft", "Brouillon", "Ébauche")
    applied = run_ts(catalog, [change], "fr", dry_run=False, finish=True).applied
    assert units(catalog)["Main.draft"].state == "translated", "finish promotes"
    assert (applied[0]["state_before"], applied[0]["state_after"]) == (
        "untranslated",
        "translated",
    ), "the promotion is recorded"


def _vanished_and_plural(tmp_path):
    path = tmp_path / "cat.ts"
    path.write_text(
        ts(
            [
                '<source>Gone</source><translation type="vanished">Parti</translation>',
                "<source>%n file(s)</source><translation><numerusform>%n fichier"
                "</numerusform><numerusform>%n fichiers</numerusform></translation>",
            ]
        ).replace("<message><source>%n", '<message numerus="yes"><source>%n'),
        encoding="utf-8",
    )
    return path, list(units(path))


def test_apply_ts_when_vanished_or_plural_mismatch_then_skips_listed(tmp_path):
    catalog, keys = _vanished_and_plural(tmp_path)
    changes = [
        candidate(keys[0], "Gone", "Parti", "Disparu"),
        candidate(keys[1], "%n file(s)", ["%n fichier", "%n fichiers"], "%n fichier"),
    ]
    outcome = run_ts(catalog, changes, "fr", dry_run=True)
    assert outcome.applied == [] and outcome.stale == [], outcome
    assert [(s["id"], s["reason"]) for s in outcome.skipped] == [
        (keys[0], "vanished"),
        (keys[1], "plural_forms"),
    ], "each skip is listed with its id and reason"


def test_apply_ts_when_plural_forms_revised_then_written(tmp_path):
    catalog, keys = _vanished_and_plural(tmp_path)
    change = candidate(
        keys[1],
        "%n file(s)",
        ["%n fichier", "%n fichiers"],
        ["%n fich.", "%n fichiers"],
    )
    outcome = run_ts(catalog, [change], "fr", dry_run=False)
    assert len(outcome.applied) == 1, outcome
    assert units(catalog)[keys[1]].plural.forms == {
        "0": "%n fich.",
        "1": "%n fichiers",
    }, "both forms written"


def _polish_numerus(tmp_path):
    forms = ["%n plik", "%n pliki", "%n plików"]
    body = "".join(f"<numerusform>{form}</numerusform>" for form in forms)
    text = ts(
        [f"<source>%n file(s)</source><translation>{body}</translation>"], "pl"
    ).replace("<message>", '<message numerus="yes">')
    path = tmp_path / "cat_pl.ts"
    path.write_text(text, encoding="utf-8")
    return path, next(iter(units(path))), forms


@pytest.mark.parametrize(
    ("language", "revised", "applied", "shape"),
    [
        ("pl", ["Jeden plik", "%n pliki", "%n plików"], 1, 0),
        ("pl", ["%n plik", "pliki", "%n plików"], 0, 1),
        ("ru", ["Jeden plik", "%n pliki", "%n plików"], 0, 1),
        ("tlh", ["Jeden plik", "%n pliki", "%n plików"], 0, 1),
    ],
)
def test_apply_review_when_plural_correction_omits_the_count_then_rule_of_language(
    tmp_path, language, revised, applied, shape
):
    catalog, key, forms = _polish_numerus(tmp_path)
    path = write_candidates(
        tmp_path / "c.jsonl", [candidate(key, "%n file(s)", forms, revised)]
    )
    result = apply_review(catalog, language, path, tmp_path / "ledger.json")
    assert (result["applied"], result["skipped"]["shape"]) == (applied, shape), (
        "only a form that one count selects in the language may omit %n"
    )
    expected = revised if applied else forms
    assert list(units(catalog)[key].plural.forms.values()) == expected, language


def test_apply_ts_when_nothing_applies_then_catalog_bytes_untouched(tmp_path):
    catalog = _catalog(
        tmp_path, "<source>Open</source><translation>Ouvrir</translation>"
    )
    before = catalog.read_bytes()
    outcome = run_ts(
        catalog,
        [candidate("Main.open", "Open", "Ouvrir", "Ouvrir")],
        "fr",
        dry_run=False,
    )
    assert outcome.counts["unchanged"] == 1 and catalog.read_bytes() == before, outcome


def test_load_candidates_when_duplicate_ids_then_refused(tmp_path):
    path = write_candidates(
        tmp_path / "c.jsonl",
        [candidate("Main.open", "Open", "Ouvrir", "Ouvrir le fichier")],
        [candidate("Main.open", "Open", "Ouvrir", "Ouvrir un fichier")],
    )
    with pytest.raises(ValueError, match="more than one candidate.*Main.open"):
        load_candidates(path, ALL_SEVERITIES, ALL_FAMILIES, set())


def test_load_candidates_when_malformed_record_then_line_named(tmp_path):
    path = tmp_path / "c.jsonl"
    path.write_text('{"model": "m", "corrections": [{"id": "x"}]}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"c\.jsonl:1: not a review record"):
        load_candidates(path, ALL_SEVERITIES, ALL_FAMILIES, set())


def test_load_candidates_when_filters_and_guards_then_counted_by_reason(tmp_path):
    path = write_candidates(
        tmp_path / "c.jsonl",
        [
            candidate("a", "Open", "Ouvrir", "Ouvrir…"),
            candidate("b", "Open", "Ouvrir", "Ouvrez", severity="minor"),
            candidate("c", "Open", "Ouvrir", "Ouvrez", family="style"),
            candidate("d", "Open", "Ouvrir", "Ouvrez"),
            candidate("e", "%n x", ["%n a", "%n b"], ["%n a"]),
            candidate("f", "Open", "Ouvrir", "Ouvrez"),
        ],
    )
    kept, filtered, refused = load_candidates(path, {"major"}, ALL_FAMILIES, {"d"})
    assert [c["id"] for c in kept] == ["f"], kept
    assert dict(filtered) == {"severity": 1, "family": 1, "rejected": 1}, filtered
    assert [(s["id"], s["reason"]) for s in refused.skipped] == [
        ("a", "shape"),
        ("e", "plural_forms"),
    ], refused.skipped


def test_load_candidates_when_markup_allowed_then_tags_change_but_colon_holds(tmp_path):
    path = write_candidates(
        tmp_path / "c.jsonl",
        [
            candidate("t", "<b>A</b>", "<b>A</b>", "<i>A</i>", family="markup"),
            candidate("c", "<b>A</b>:", "<b>A</b>:", "<i>A</i>", family="markup"),
        ],
    )
    kept, _, refused = load_candidates(
        path, ALL_SEVERITIES, ALL_FAMILIES, set(), allow_markup=True
    )
    assert [c["id"] for c in kept] == ["t"], "the tag repair is kept"
    assert [s["reason"] for s in refused.skipped] == ["shape"], "the lost colon is not"


def test_apply_review_when_run_then_ledger_lists_changes_skips_and_stale(tmp_path):
    catalog, keys = _vanished_and_plural(tmp_path)
    path = write_candidates(
        tmp_path / "c.jsonl",
        [
            candidate(keys[0], "Gone", "Parti", "Disparu"),
            candidate(keys[1], "%n file(s)", ["%n fichier", "%n fichiers"], ["%n f"]),
            candidate("Main.missing", "X", "Y", "Z"),
        ],
    )
    ledger = tmp_path / "out" / "ledger.json"
    summary = apply_review(catalog, "fr", path, ledger, scope="Test scope.")
    written = json.loads(ledger.read_text(encoding="utf-8"))
    assert written["scope"] == "Test scope.", written
    assert written["skipped"]["vanished"] == 1, written["skipped"]
    assert written["skipped"]["plural_forms"] == 1, written["skipped"]
    assert written["skipped"]["stale"] == 1, written["skipped"]
    assert {s["id"] for s in written["skipped_items"]} == set(keys), written
    assert summary["skipped_ids"] == {
        "plural_forms": [keys[1]],
        "vanished": [keys[0]],
    }, summary


def test_apply_review_when_dry_run_then_no_ledger_and_catalog_untouched(tmp_path):
    catalog = _catalog(
        tmp_path, "<source>Open</source><translation>Ouvrir</translation>"
    )
    before = catalog.read_bytes()
    path = write_candidates(
        tmp_path / "c.jsonl", [candidate("Main.open", "Open", "Ouvrir", "Ouvrez")]
    )
    ledger = tmp_path / "ledger.json"
    summary = apply_review(catalog, "fr", path, ledger, dry_run=True)
    assert summary["applied"] == 1 and summary["dry_run"], summary
    assert not ledger.exists() and catalog.read_bytes() == before, "nothing written"


def test_apply_review_when_json_without_source_then_refused(tmp_path):
    target = tmp_path / "help_fr.json"
    target.write_text("{}", encoding="utf-8")
    path = write_candidates(tmp_path / "c.jsonl", [])
    with pytest.raises(ValueError, match="English source JSON"):
        apply_review(target, "fr", path, tmp_path / "l.json")


def test_apply_review_when_clean_run_then_every_skip_reason_reported_as_zero(tmp_path):
    catalog = _catalog(
        tmp_path, "<source>Open</source><translation>Ouvrir</translation>"
    )
    path = write_candidates(
        tmp_path / "c.jsonl", [candidate("Main.open", "Open", "Ouvrir", "Ouvrez")]
    )
    summary = apply_review(catalog, "fr", path, tmp_path / "l.json")
    assert summary["applied"] == 1, summary
    assert summary["skipped"] == dict.fromkeys(SKIP_REASONS, 0), summary["skipped"]
