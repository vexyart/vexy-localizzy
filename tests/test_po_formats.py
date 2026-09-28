# this_file: tests/test_po_formats.py
"""Gettext context, comment and plural fidelity through canonical catalogs."""

import polib
import pytest

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.formats import json_io, po

SOURCE = """# Catalog note
msgid ""
msgstr ""
"Project-Id-Version: Synthetic 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Language: pl\\n"
"Plural-Forms: nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<12 || n%100>14) ? 1 : 2);\\n"
"X-Source-Language: en\\n"
"X-Custom: retained\\n"

# An obsolete entry may precede active entries.
#~ msgctxt "old"
#~ msgid "Earlier"
#~ msgstr "Old translation"

# Translator note
#. Developer note
#: app.py:12 view.ui:4
#, fuzzy, python-format
#| msgctxt "previous"
#| msgid "Old %s"
msgctxt "menu"
msgid "Open %s"
msgstr "Otwórz %s"

msgctxt "verb"
msgid "Open %s"
msgstr ""

# Plural note
#, c-format
msgid "%d item"
msgid_plural "%d items"
msgstr[0] "%d element"
msgstr[1] "%d elementy"
msgstr[2] "%d elementów"
"""


def edit(catalog, index, **updates):
    units = list(catalog.units)
    units[index] = units[index].model_copy(update=updates)
    return catalog.model_copy(update={"units": units})


def test_po_when_roundtripped_through_json_then_original_bytes_and_plural_sources_survive(
    tmp_path,
):
    path = tmp_path / "input.po"
    raw = SOURCE.replace("\n", "\r\n").encode()
    path.write_bytes(raw)
    catalog = po.load(path)
    assert len(catalog.units) == 4
    assert catalog.units[0].state == "vanished"
    assert catalog.units[1].state == "needs_review"
    assert catalog.units[1].notes == ["Translator note", "Developer note"]
    assert catalog.units[2].target == ""
    assert catalog.units[3].source_plural == "%d items"
    assert catalog.units[3].plural.indexing == "index"
    assert catalog.units[3].plural.forms == {
        "0": "%d element",
        "1": "%d elementy",
        "2": "%d elementów",
    }
    assert len({unit.key for unit in catalog.units}) == 4
    json_io.dump(catalog, tmp_path / "saved.json")
    path.unlink()
    po.dump(json_io.load(tmp_path / "saved.json"), tmp_path / "out.po")
    assert (tmp_path / "out.po").read_bytes() == raw


def test_po_when_editing_translation_then_context_comments_flags_previous_and_order_preserved(
    tmp_path,
):
    path = tmp_path / "input.po"
    path.write_text(SOURCE)
    catalog = edit(po.load(path), 1, target='Otwórz "nowy" %s\n', state="approved")
    output = tmp_path / "out.po"
    po.dump(catalog, output)
    before, after = polib.pofile(str(path)), polib.pofile(str(output))
    assert before.metadata == after.metadata
    assert before.header == after.header
    assert [e.msgid for e in after] == [e.msgid for e in before]
    assert after[1].msgstr == 'Otwórz "nowy" %s\n'
    assert after[1].flags == ["python-format"]
    for i in range(4):
        left, right = vars(before[i]).copy(), vars(after[i]).copy()
        ignored = {"linenum", "msgstr", "flags"} if i == 1 else {"linenum"}
        assert {k: v for k, v in left.items() if k not in ignored} == {
            k: v for k, v in right.items() if k not in ignored
        }


def test_po_when_plural_edited_then_all_indices_and_rule_preserved(tmp_path):
    path = tmp_path / "input.po"
    path.write_text(SOURCE)
    catalog = po.load(path)
    plural = catalog.units[3].plural.model_copy(
        update={"forms": {"0": "Jeden", "1": "Kilka", "2": "Wiele"}}
    )
    output = tmp_path / "out.po"
    po.dump(edit(catalog, 3, plural=plural), output)
    assert po.load(output).units[3].plural == plural
    assert (
        polib.pofile(str(output)).metadata["Plural-Forms"]
        == polib.pofile(str(path)).metadata["Plural-Forms"]
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"context": "changed"},
        {"source": "changed"},
        {"notes": []},
        {"record_id": "po:900"},
        {"target": None},
        {"source_plural": "changed"},
    ],
)
def test_po_when_unsupported_edit_then_existing_output_survives(tmp_path, updates):
    path = tmp_path / "input.po"
    path.write_text(SOURCE)
    output = tmp_path / "out.po"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        po.dump(edit(po.load(path), 1, **updates), output)
    assert output.read_bytes() == b"existing"


def test_po_when_original_encoding_cannot_represent_edit_then_fail_atomically(tmp_path):
    path = tmp_path / "input.po"
    path.write_bytes(
        'msgid ""\nmsgstr "Content-Type: text/plain; charset=ISO-8859-1\\n"\n\nmsgid "Cafe"\nmsgstr "Café"\n'.encode(
            "latin1"
        )
    )
    catalog = po.load(path)
    output = tmp_path / "out.po"
    po.dump(catalog, output)
    assert output.read_bytes() == path.read_bytes()
    with pytest.raises(UnicodeEncodeError):
        po.dump(edit(catalog, 0, target="Łąka"), output)
    assert output.read_bytes() == path.read_bytes()


def test_po_when_fresh_plural_catalog_then_explicit_source_and_rule_required(tmp_path):
    catalog = Catalog(
        source_lang="en",
        target_lang="pl",
        units=[
            Unit(
                key="items",
                context="",
                source="%d item",
                source_plural="%d items",
                plural=PluralForms(
                    indexing="index", forms={"0": "Jeden", "1": "Kilka", "2": "Wiele"}
                ),
                state="translated",
            )
        ],
    )
    output = tmp_path / "out.po"
    with pytest.raises(ValueError, match="Plural-Forms"):
        po.dump(catalog, output)
    po.dump(
        catalog, output, plural_forms="nplurals=3; plural=(n==1 ? 0 : n==2 ? 1 : 2);"
    )
    recovered = po.load(output)
    assert recovered.units[0].source_plural == "%d items"
    assert recovered.units[0].plural == catalog.units[0].plural


@pytest.mark.parametrize(
    "raw",
    [
        b"not a catalog",
        b'msgid "broken\nmsgstr "A"',
        b"\xff\xfeinvalid",
        b'msgid """bad"""\nmsgstr "A"',
    ],
)
def test_po_when_invalid_input_then_reject(tmp_path, raw):
    path = tmp_path / "bad.po"
    path.write_bytes(raw)
    with pytest.raises((ValueError, OSError)):
        po.load(path)


@pytest.mark.parametrize(
    "forms", [{}, {"0": "one"}, {"0": "one", "1": "two", "2": "three"}]
)
def test_po_when_plural_count_disagrees_with_rule_then_no_write(tmp_path, forms):
    catalog = Catalog(
        source_lang="en",
        units=[
            Unit(
                key="a",
                context="",
                source="item",
                source_plural="items",
                plural=PluralForms(indexing="index", forms=forms),
            )
        ],
    )
    output = tmp_path / "out.po"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError, match="plural"):
        po.dump(catalog, output, plural_forms="nplurals=2; plural=n!=1;")
    assert output.read_bytes() == b"existing"


def test_po_when_retained_plural_rule_count_changes_then_no_write(tmp_path):
    source = tmp_path / "input.po"
    source.write_text(SOURCE)
    with pytest.raises(ValueError, match="plural"):
        po.dump(
            po.load(source),
            tmp_path / "out.po",
            plural_forms="nplurals=2; plural=n!=1;",
        )
    assert not (tmp_path / "out.po").exists()


@pytest.mark.parametrize("forms", ["", 'msgstr[0] "one"\n'])
def test_po_when_plural_incomplete_then_untranslated_and_raw_preserved(tmp_path, forms):
    source = tmp_path / "input.po"
    raw = (
        'msgid ""\nmsgstr "Plural-Forms: nplurals=2; plural=n!=1;\\n"\n\nmsgid "item"\nmsgid_plural "items"\n'
        + forms
    )
    source.write_text(raw)
    catalog = po.load(source)
    assert catalog.units[0].state == "untranslated"
    po.dump(catalog, tmp_path / "out.po")
    assert (tmp_path / "out.po").read_text() == raw


def test_po_when_source_language_edited_then_header_updated(tmp_path):
    source = tmp_path / "input.po"
    source.write_text(SOURCE)
    catalog = po.load(source).model_copy(update={"source_lang": "fr"})
    output = tmp_path / "out.po"
    po.dump(catalog, output)
    assert po.load(output).source_lang == "fr"
    assert polib.pofile(str(output)).metadata["X-Source-Language"] == "fr"


@pytest.mark.parametrize(
    "rule",
    [
        "nplurals=0; plural=0;",
        "nplurals=2; plural=garbage;",
        "nplurals=2;",
        "nplurals=2; plural=2;",
    ],
)
def test_po_when_plural_rule_invalid_then_refuse_output(tmp_path, rule):
    source = tmp_path / "input.po"
    source.write_text(SOURCE)
    with pytest.raises(ValueError, match="plural|Plural"):
        po.dump(po.load(source), tmp_path / "out.po", plural_forms=rule)
    assert not (tmp_path / "out.po").exists()
