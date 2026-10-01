# this_file: tests/upgrade/test_diff.py
"""Catalog diff: upgrade-style pairing, the four report sections and Markdown rendering."""

from pathlib import Path

import pytest

from vexy_localizzy.upgrade.diff import (
    compare,
    pair_messages,
    read_messages,
    render,
    text_of,
)


def ts(*contexts: tuple[str, list[str]], language: str = "de_DE") -> bytes:
    """TS bytes; each context is (name, [<message> inner XML or full <message ...>])."""
    body = ""
    for name, messages in contexts:
        items = "".join(
            m if m.startswith("<message") else f"<message>{m}</message>"
            for m in messages
        )
        body += f"<context><name>{name}</name>{items}</context>\n"
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
        f'<TS version="2.1" language="{language}" sourcelanguage="en">\n{body}</TS>\n'
    ).encode()


def msg(source: str, target: str = "", kind: str | None = None, **attrs) -> str:
    extra = "".join(f' {k}="{v}"' for k, v in attrs.items())
    status = f' type="{kind}"' if kind else ""
    return (
        f"<message{extra}><source>{source}</source>"
        f"<translation{status}>{target}</translation></message>"
    )


def write(tmp_path: Path, name: str, raw: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(raw)
    return path


def test_read_messages_when_plural_form_empty_then_not_filled():
    plural = (
        '<message numerus="yes"><source>%n file(s)</source><translation>'
        "<numerusform>eine</numerusform><numerusform></numerusform>"
        "</translation></message>"
    )
    messages = read_messages(ts(("A", [plural, msg("Open", "Öffnen")])))
    assert [m.filled for m in messages] == [False, True], "every plural slot counts"
    assert messages[1].unit.target == "Öffnen", "unit and ref stay aligned"


def test_pair_messages_when_only_new_side_has_id_then_key_fallback():
    old = read_messages(ts(("A", [msg("Open", "Öffnen")])))
    new = read_messages(ts(("A", [msg("Open", id="open.id")])))
    assert pair_messages(old, new) == {0: 0}, "a fresh id unknown to old pairs by key"


def test_pair_messages_when_old_has_id_then_source_change_still_pairs():
    old = read_messages(ts(("A", [msg("Open", "Öffnen", id="x")])))
    new = read_messages(ts(("A", [msg("Open…", id="x")])))
    assert pair_messages(old, new) == {0: 0}, "ids win over changed source text"


def test_pair_messages_when_keys_repeat_then_first_come_first_served():
    old = read_messages(ts(("A", [msg("Open", "1"), msg("Open", "2")])))
    new = read_messages(ts(("A", [msg("Open"), msg("Open"), msg("Open")])))
    assert pair_messages(old, new) == {0: 0, 1: 1}, "the third copy is unpaired"


def test_text_of_when_plural_or_scalar_then_list_or_string():
    plural = (
        '<message numerus="yes"><source>%n x</source><translation>'
        "<numerusform>b</numerusform><numerusform>c</numerusform></translation></message>"
    )
    first, second = read_messages(ts(("A", [plural, msg("Open")])))
    assert text_of(first.unit) == ["b", "c"], "plural forms in index order"
    assert text_of(second.unit) == "", "an empty scalar is an empty string"


def test_compare_when_catalogs_differ_then_four_sections(tmp_path):
    old = write(
        tmp_path,
        "old.ts",
        ts(
            (
                "A",
                [
                    msg("Open", "Öffnen"),
                    msg("Save", "Sichern"),
                    msg("Quit", "Beenden"),
                    msg("Gone", "Weg", kind="vanished"),
                ],
            )
        ),
    )
    new = write(
        tmp_path,
        "new.ts",
        ts(
            (
                "A",
                [
                    msg("Open", "Öffnen"),
                    msg("Save", "Speichern"),
                    msg("Close", kind="unfinished"),
                    msg("Print", "Drucken"),
                ],
            )
        ),
    )
    report = compare(old, new)
    assert [r["source"] for r in report["new_untranslated"]] == ["Close"], report
    assert [r["source"] for r in report["new_translated"]] == ["Print"], report
    assert report["changed"] == [
        {
            "context": "A",
            "source": "Save",
            "comment": "",
            "old": "Sichern",
            "new": "Speichern",
            "old_state": "translated",
            "new_state": "translated",
        }
    ], report["changed"]
    assert [r["source"] for r in report["removed"]] == ["Quit"], "vanished is ignored"
    assert report["counts"]["old_messages"] == 3, "vanished messages are not counted"


def test_compare_when_catalogs_empty_then_zero_counts(tmp_path):
    old = write(tmp_path, "old.ts", ts())
    new = write(tmp_path, "new.ts", ts())
    counts = compare(old, new)["counts"]
    assert set(counts.values()) == {0}, counts


def test_compare_when_file_missing_then_error(tmp_path):
    new = write(tmp_path, "new.ts", ts())
    with pytest.raises(FileNotFoundError):
        compare(tmp_path / "missing.ts", new)


def test_render_when_sections_present_then_markdown_lists_them(tmp_path):
    old = write(tmp_path, "old.ts", ts(("A", [msg("Save", "Sichern")])))
    new = write(
        tmp_path,
        "new.ts",
        ts(
            (
                "A",
                [
                    "<message><source>Save</source><comment>menu</comment>"
                    "<translation>Speichern</translation></message>"
                ],
            )
        ),
    )
    text = render(compare(old, new))
    assert "## New in the fresh catalog, already translated (1)" in text, text
    assert "    new: 'Speichern'" in text, "a filled new translation is shown"
    assert "## Removed from the fresh catalog (1)" in text, "comment changes identity"
    assert "Translation differs" not in text, "empty sections are omitted"
    assert "| 'menu'" in text, "a comment is shown next to its source"


def test_pair_messages_when_id_known_only_from_retired_message_then_unpaired():
    old = read_messages(
        ts(("A", [msg("Open", "Öffnen", kind="vanished", id="x"), msg("Open", "Auf")]))
    )
    new = read_messages(ts(("A", [msg("Open", id="x")])))
    assert pair_messages(old, new) == {}, "upgrade does not fall back to the key here"
