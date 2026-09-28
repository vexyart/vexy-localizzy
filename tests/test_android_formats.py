# this_file: tests/test_android_formats.py
"""Android resource preservation and single-column conversion boundaries."""

from copy import deepcopy

import pytest
from lxml import etree

from vexy_localizzy.catalog import Catalog, PluralForms, Unit
from vexy_localizzy.conversion import ConversionLoss, convert
from vexy_localizzy.formats import android

SOURCE = r"""<?xml version="1.0"?>
<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2" xmlns:tools="http://schemas.android.com/tools">
<!-- retained comment -->
<string name="open" tools:ignore="TypographyQuotes">  Open   now  </string>
<string name="quoted">"  Exact   spacing  "</string>
<string name="escape">It\'s \"open\"\n\u0141\q</string>
<string name="styled">Hello <b>bold</b>, <xliff:g id="person">%1$s</xliff:g>!</string>
<string name="literal">&lt;b&gt;literal&lt;/b&gt;</string>
<string name="fixed" translatable="false">Constant</string>
<string name="reference">@string/open</string>
<plurals name="items"><item quantity="one">%d item</item><item quantity="other">%d items</item></plurals>
<string-array name="choices"><item>First</item><item>Second</item></string-array>
<integer name="count">12</integer>
</resources>"""


def test_android_when_json_roundtrip_then_bytes_all_units_and_metadata_survive(
    tmp_path,
):
    source = tmp_path / "strings.xml"
    raw = SOURCE.replace("\n", "\r\n").encode()
    source.write_bytes(raw)
    catalog = android.load(source)
    assert len(catalog.units) == 10
    by = {unit.key: unit for unit in catalog.units}
    assert by["open"].source == "Open now"
    assert by["quoted"].source == "  Exact   spacing  "
    assert by["escape"].source == 'It\'s "open"\nŁq'
    assert by["literal"].source == "<b>literal</b>"
    assert by["items"].plural.forms == {"one": "%d item", "other": "%d items"}
    assert by["choices[1]"].source == "Second"
    convert(source, "json", tmp_path / "saved.json")
    convert(tmp_path / "saved.json", "android", tmp_path / "out.xml")
    assert (tmp_path / "out.xml").read_bytes() == raw


def test_android_when_target_empty_then_write_empty_and_preserve_other_nodes(tmp_path):
    source = tmp_path / "strings.xml"
    source.write_text(SOURCE)
    catalog = android.load(source)
    units = list(catalog.units)
    units[0] = units[0].model_copy(update={"target": ""})
    output = tmp_path / "out.xml"
    android.dump(catalog.model_copy(update={"units": units}), output)
    assert android.load(output).units[0].source == ""
    before, after = [etree.parse(str(path)) for path in (source, output)]
    old, new = [tree.getroot().find("string") for tree in (before, after)]
    before.getroot().replace(old, deepcopy(new))
    assert etree.tostring(before) == etree.tostring(after)


def test_android_when_inline_edited_then_styling_and_placeholder_codes_survive(
    tmp_path,
):
    source = tmp_path / "strings.xml"
    source.write_text(SOURCE)
    catalog = android.load(source)
    units = list(catalog.units)
    index = next(i for i, u in enumerate(units) if u.key == "styled")
    units[index] = units[index].model_copy(
        update={
            "target": units[index]
            .source.replace("Hello", "Bonjour")
            .replace("bold", "gras")
        }
    )
    android.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.xml")
    out = etree.parse(str(tmp_path / "out.xml"))
    logical = android.load(tmp_path / "out.xml").units[index].source
    assert (
        etree.fromstring(("<fragment>" + logical + "</fragment>").encode())
        .find("b")
        .text
        == "gras"
    )
    assert (
        out.find('string[@name="styled"]/{urn:oasis:names:tc:xliff:document:1.2}g').get(
            "id"
        )
        == "person"
    )


@pytest.mark.parametrize(
    "key,updates",
    [
        ("fixed", {"target": "change"}),
        ("reference", {"target": "change"}),
        ("styled", {"target": "codes gone"}),
        ("open", {"source": "change"}),
        ("items", {"plural": PluralForms(forms={"other": "changed"})}),
    ],
)
def test_android_when_unsupported_edit_then_destination_preserved(
    tmp_path, key, updates
):
    source = tmp_path / "strings.xml"
    source.write_text(SOURCE)
    catalog = android.load(source)
    units = [
        unit.model_copy(update=updates) if unit.key == key else unit
        for unit in catalog.units
    ]
    output = tmp_path / "out.xml"
    output.write_bytes(b"existing")
    with pytest.raises(ValueError):
        android.dump(catalog.model_copy(update={"units": units}), output)
    assert output.read_bytes() == b"existing"


def test_android_when_array_and_plural_edited_then_original_shape_survives(tmp_path):
    source = tmp_path / "strings.xml"
    source.write_text(SOURCE)
    catalog = android.load(source)
    units = []
    for unit in catalog.units:
        updates = (
            {"target": "Deuxième"}
            if unit.key == "choices[1]"
            else {
                "plural": PluralForms(
                    forms={"one": "%d élément", "other": "%d éléments"}
                )
            }
            if unit.key == "items"
            else {}
        )
        units.append(unit.model_copy(update=updates))
    android.dump(catalog.model_copy(update={"units": units}), tmp_path / "out.xml")
    tree = etree.parse(str(tmp_path / "out.xml"))
    assert len(tree.findall("string-array/item")) == 2
    assert android.load(tmp_path / "out.xml").units[-1].source == "Deuxième"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "  a   b  ",
        "@string/open",
        "?attr/name",
        'It\'s "open"',
        "Line\nTab\tCR\rSlash\\",
        "Łódź 日本語 😀",
    ],
)
def test_android_when_fresh_values_then_escape_roundtrip(tmp_path, value):
    catalog = Catalog(
        source_lang="en", units=[Unit(key="sample", context="", source=value)]
    )
    android.dump(catalog, tmp_path / "out.xml")
    assert android.load(tmp_path / "out.xml").units[0].source == value


def test_android_when_bilingual_conversion_then_losses_require_acknowledgement(
    tmp_path,
):
    source = tmp_path / "in.ts"
    source.write_text(
        '<TS language="fr"><context><name>C</name><message id="open"><source>Open</source><translation>Ouvrir</translation></message></context></TS>'
    )
    with pytest.raises(ConversionLoss) as error:
        convert(source, "android", tmp_path / "out.xml")
    assert {"source", "target", "document"} <= {
        finding.data["field"] for finding in error.value.findings
    }
    convert(source, "android", tmp_path / "out.xml", allow_loss=True)
    assert android.load(tmp_path / "out.xml").units[0].source == "Ouvrir"


@pytest.mark.parametrize(
    "body",
    [
        '<string name="a">one</string><string name="a">two</string>',
        '<plurals name="n"><item quantity="bad">x</item></plurals>',
        '<plurals name="n"><item quantity="one">x</item><item quantity="one">y</item></plurals>',
        '<string name="a">bad\\uZZZZ</string>',
    ],
)
def test_android_when_invalid_resource_then_reject(tmp_path, body):
    source = tmp_path / "strings.xml"
    source.write_text("<resources>" + body + "</resources>")
    with pytest.raises(ValueError):
        android.load(source)


def test_android_when_names_shared_across_types_then_json_roundtrip_preserves_bytes(
    tmp_path,
):
    source = tmp_path / "strings.xml"
    raw = (
        b'<resources><string name="same">One</string>'
        b'<plurals name="same"><item quantity="one">One</item>'
        b'<item quantity="other">Many</item></plurals></resources>'
    )
    source.write_bytes(raw)
    convert(source, "json", tmp_path / "catalog.json")
    convert(tmp_path / "catalog.json", "android", tmp_path / "restored.xml")
    assert (tmp_path / "restored.xml").read_bytes() == raw


@pytest.mark.parametrize("quoted", [False, True])
def test_android_when_only_placeholder_markup_then_trim_only_unquoted_outer_spaces(
    tmp_path, quoted
):
    source = tmp_path / "strings.xml"
    quote = '"' if quoted else ""
    source.write_text(
        '<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">'
        f'<string name="person">{quote}  Hello '
        f'<xliff:g id="x">%1$s</xliff:g>  {quote}</string></resources>'
    )
    catalog = android.load(source)
    unit = catalog.units[0]
    fragment = etree.fromstring(("<fragment>" + unit.source + "</fragment>").encode())
    assert "".join(fragment.itertext()) == (
        "  Hello %1$s  " if quoted else "Hello %1$s"
    ), "Transparent placeholders must follow the plain-string whitespace rules"
    android.dump(
        catalog.model_copy(
            update={"units": [unit.model_copy(update={"target": unit.source})]}
        ),
        tmp_path / "out.xml",
    )
    assert android.load(tmp_path / "out.xml").units[0].source == unit.source
