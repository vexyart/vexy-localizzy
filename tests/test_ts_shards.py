# this_file: tests/test_ts_shards.py
"""TS shards: balanced split by whole context, merge back by message identity."""

from pathlib import Path

import pytest

from vexy_localizzy.catalog import PluralForms, Unit
from vexy_localizzy.formats.ts import load
from vexy_localizzy.formats.ts_shards import (
    balance,
    check_language,
    clear_shards,
    fill,
    glob_escape,
    merge,
    needs_text,
    shard_name,
    split,
)


def ts(body: str, language: str = "fr_FR") -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
        f'<TS version="2.1" language="{language}" sourcelanguage="en">\n{body}</TS>\n'
    )


def context(name: str, *messages: str) -> str:
    return f"<context><name>{name}</name>{''.join(messages)}</context>\n"


def msg(source: str, target: str = "", attrs: str = "") -> str:
    return (
        f"<message{attrs}><source>{source}</source>"
        f"<translation>{target}</translation></message>"
    )


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def targets(path: Path) -> dict[str, str | None]:
    return {u.source: u.target for u in load(path).units}


@pytest.fixture
def fixture(tmp_path):
    """An English catalog with contexts A and B, and one translated shard each."""
    en = write(
        tmp_path / "app_en.ts",
        ts(context("A", msg("Open")) + context("B", msg("Save")), language="en"),
    )
    shard_a = write(tmp_path / "a_fr.ts", ts(context("A", msg("Open", "Ouvrir"))))
    shard_b = write(tmp_path / "b_fr.ts", ts(context("B", msg("Save", "Enregistrer"))))
    return en, shard_a, shard_b


def test_balance_when_sizes_uneven_then_largest_first_into_lightest():
    assert balance([5, 1, 3, 3], 2) == [[0, 1], [2, 3]], "loads 6 and 6"


def test_balance_when_parts_not_positive_then_value_error():
    with pytest.raises(ValueError):
        balance([1], 0)


def test_split_when_parts_exceed_contexts_then_empty_shards_skipped(tmp_path, fixture):
    en, _, _ = fixture
    rows = split(en, tmp_path / "shards", 5)
    assert [r["contexts"] for r in rows] == [1, 1], rows
    names = sorted(Path(r["path"]).name for r in rows)
    assert names == ["app_en-shard1.ts", "app_en-shard2.ts"], names
    contexts = [{u.context for u in load(Path(r["path"])).units} for r in rows]
    assert sorted(map(sorted, contexts)) == [["A"], ["B"]], "contexts stay whole"


def test_split_when_messages_outside_context_then_first_shard_only(tmp_path):
    source = write(
        tmp_path / "app.ts",
        ts(msg("Loose") + context("A", msg("Open")) + context("B", msg("Save"))),
    )
    rows = split(source, tmp_path / "out", 2)
    sources = [[u.source for u in load(Path(r["path"])).units] for r in rows]
    assert sum("Loose" in s for s in sources) == 1, sources
    assert sum(r["messages"] for r in rows) == 3, rows


def test_needs_text_when_vanished_or_empty_source_then_false():
    assert needs_text(Unit(context="A", key="a", source="Open")), (
        "an active message with source needs text"
    )
    assert not needs_text(Unit(context="A", key="b", source="  ")), "empty source"
    assert not needs_text(Unit(context="A", key="c", source="Old", state="vanished")), (
        "vanished"
    )


def test_fill_when_shapes_differ_then_none_else_copied():
    plural = PluralForms(indexing="index", forms={"0": "", "1": ""})
    unit = Unit(context="A", key="n", source="%n x", plural=plural)
    three = PluralForms(indexing="index", forms={"0": "a", "1": "b", "2": "c"})
    assert (
        fill(unit, Unit(context="A", key="n", source="%n x", plural=three)) is None
    ), "count"
    assert fill(unit, Unit(context="A", key="n", source="%n x", target="a")) is None, (
        "shape"
    )
    two = PluralForms(indexing="index", forms={"0": "a", "1": "b"})
    filled = fill(
        unit, Unit(context="A", key="n", source="%n x", plural=two, state="translated")
    )
    assert filled.plural.forms == {"0": "a", "1": "b"}, filled
    scalar = fill(
        Unit(context="A", key="s", source="Open"),
        Unit(context="A", key="s", source="Open", target="O"),
    )
    assert scalar.target == "O", scalar


def test_merge_when_output_exists_without_force_then_refused(tmp_path, fixture):
    en, shard_a, shard_b = fixture
    out = write(tmp_path / "app_fr.ts", "keep")
    with pytest.raises(FileExistsError):
        merge(en, [shard_a, shard_b], target="fr_FR", plural_count=2, out=out)
    assert out.read_text(encoding="utf-8") == "keep", "the file is untouched"


def test_merge_when_shard_missing_then_unfilled_counted_and_written(tmp_path, fixture):
    en, shard_a, shard_b = fixture
    out = tmp_path / "app_fr.ts"
    summary = merge(en, [shard_a], target="fr_FR", plural_count=2, out=out)
    assert (summary["filled"], summary["unfilled"]) == (1, 1), summary
    assert targets(out) == {"Open": "Ouvrir", "Save": ""}, "written for inspection"
    summary = merge(
        en, [shard_a, shard_b], target="fr_FR", plural_count=2, out=out, force=True
    )
    assert summary["unfilled"] == 0, summary
    assert targets(out) == {"Open": "Ouvrir", "Save": "Enregistrer"}, (
        "both shards fill the template"
    )
    assert load(out).target_lang == "fr-FR", "the template takes the target language"


def test_merge_when_shard_plural_forms_empty_then_counted_unfilled(tmp_path):
    numerus = ' numerus="yes"'
    en = write(
        tmp_path / "app_en.ts",
        ts(context("A", msg("%n file(s)", attrs=numerus)), language="en"),
    )
    forms = "<numerusform></numerusform><numerusform></numerusform>"
    shard = write(
        tmp_path / "s_fr.ts", ts(context("A", msg("%n file(s)", forms, numerus)))
    )
    summary = merge(en, [shard], target="fr_FR", plural_count=2, out=tmp_path / "o.ts")
    assert summary["unfilled"] == 1, "a plural with empty forms is not a fill"


def test_merge_when_message_ids_then_paired_by_id(tmp_path):
    en = write(
        tmp_path / "app_en.ts",
        ts(context("A", msg("Open", attrs=' id="open"')), language="en"),
    )
    shard = write(
        tmp_path / "s_fr.ts",
        ts(context("Other", msg("Open (old)", "Ouvrir", ' id="open"'))),
    )
    summary = merge(en, [shard], target="fr_FR", plural_count=2, out=tmp_path / "o.ts")
    assert summary["unfilled"] == 0 and targets(tmp_path / "o.ts") == {
        "Open": "Ouvrir"
    }, summary


def test_merge_when_catalog_empty_then_nothing_to_fill(tmp_path):
    en = write(tmp_path / "app_en.ts", ts("", language="en"))
    summary = merge(en, [], target="fr_FR", plural_count=2, out=tmp_path / "o.ts")
    assert (summary["messages"], summary["unfilled"]) == (0, 0), summary
    assert (tmp_path / "o.ts").exists(), "an empty catalog is still written"


def test_split_then_merge_when_every_shard_translated_then_complete(tmp_path, fixture):
    en, _, _ = fixture
    translated = []
    for row in split(en, tmp_path / "shards", 2):
        path = Path(row["path"])
        text = (
            path.read_text(encoding="utf-8")
            .replace("<translation/>", "<translation>FR</translation>")
            .replace('language="en"', 'language="fr"')
        )
        translated.append(write(path.with_name(path.stem + "_fr.ts"), text))
    summary = merge(en, translated, target="fr", plural_count=2, out=tmp_path / "o.ts")
    assert summary["unfilled"] == 0, summary
    assert set(targets(tmp_path / "o.ts").values()) == {"FR"}, (
        "every message took the shard text"
    )


def test_fill_when_length_variants_then_copied_when_counts_match():
    unit = Unit(context="A", key="v", source="Open", variants=["", ""])
    hit = Unit(context="A", key="v", source="Open", variants=["Ouvrir", "Ouv."])
    assert fill(unit, hit).variants == ["Ouvrir", "Ouv."], "variants copied"
    short = Unit(context="A", key="v", source="Open", variants=["Ouvrir"])
    assert fill(unit, short) is None, "a different variant count is not a fill"


def test_split_when_shards_exist_then_refused_unless_force_removes_stale(tmp_path):
    source = write(
        tmp_path / "app.ts",
        ts(context("A", msg("Open")) + context("B", msg("Save")), language="en"),
    )
    out = tmp_path / "shards"
    split(source, out, 2)
    translated = write(out / "app-shard1_fr.ts", "translated work")
    with pytest.raises(FileExistsError, match="app-shard1.ts"):
        split(source, out, 1)
    assert translated.read_text(encoding="utf-8") == "translated work", "kept"
    rows = split(source, out, 1, force=True)
    assert [Path(r["path"]).name for r in rows] == ["app-shard1.ts"], rows
    assert not (out / "app-shard2.ts").exists(), "the stale second shard is removed"
    assert translated.exists(), "force removes only the split's own shard files"


def test_clear_shards_when_force_then_only_numbered_shards_removed(tmp_path):
    own, other = tmp_path / "x-shard3.ts", tmp_path / "x-shard3_de.ts"
    own.write_text("a", encoding="utf-8")
    other.write_text("b", encoding="utf-8")
    assert clear_shards(tmp_path / "x.ts", tmp_path, force=True) == [own], "own only"
    assert other.exists() and not own.exists(), "translations survive"
    assert clear_shards(tmp_path / "y.ts", tmp_path, force=False) == [], "no shards"


def test_shard_name_when_stem_has_glob_characters_then_matched_literally(tmp_path):
    assert shard_name(Path("a[1].ts"), 2) == "a[1]-shard2.ts", "stem plus part"
    assert glob_escape("a[1]*?") == "a[[]1][*][?]", "metacharacters escaped"
    write(tmp_path / "a1-shard1.ts", "other catalog")
    assert clear_shards(tmp_path / "a[1].ts", tmp_path, force=False) == [], (
        "a[1] does not match a1"
    )


def test_check_language_when_region_differs_then_refused():
    check_language(Path("s.ts"), "fr", "fr-FR")
    check_language(Path("s.ts"), "fr_FR", "fr")
    with pytest.raises(ValueError, match="fr_CA"):
        check_language(Path("s.ts"), "fr_CA", "fr-FR")
    with pytest.raises(ValueError, match="no language"):
        check_language(Path("s.ts"), None, "fr")


def test_merge_when_shard_language_differs_then_refused(tmp_path, fixture):
    en, shard_a, _ = fixture
    german = write(
        tmp_path / "de.ts", ts(context("B", msg("Save", "Sichern")), "de_DE")
    )
    out = tmp_path / "o.ts"
    with pytest.raises(ValueError, match="de_DE"):
        merge(en, [shard_a, german], target="fr_FR", plural_count=2, out=out)
    assert not out.exists(), "nothing is written"


def test_merge_when_out_is_an_input_then_refused(tmp_path, fixture):
    en, shard_a, _ = fixture
    before = en.read_bytes()
    with pytest.raises(ValueError, match="input"):
        merge(en, [shard_a], target="fr_FR", plural_count=2, out=en, force=True)
    assert en.read_bytes() == before, "the source catalog is untouched"
