# this_file: tests/test_legacy_pairs.py
"""Explicit legacy TMX projections retain ordering, eligibility and plural policy."""

import xml.etree.ElementTree as ET

import polib
import pytest

from vexy_localizzy.legacy_pairs import po_pairs, ts_pairs


def test_ts_pairs_when_mixed_states_then_select_finished_first_and_last_forms():
    root = ET.fromstring("""<TS><context><name> Dialog </name>
      <message><source>Open</source><translation>Otwórz</translation></message>
      <message><source>Skip</source><translation type="unfinished">Pomiń</translation></message>
      <message numerus="yes"><source>%n items</source><translation>
        <numerusform></numerusform><numerusform>%n rzecz</numerusform>
        <numerusform>%n rzeczy</numerusform><numerusform>%n rzeczy wielu</numerusform>
      </translation></message>
      <message><source>Absent</source></message>
      <message><source></source><translation>Nothing</translation></message>
      <message><source>Open</source><translation>Otwórz</translation></message>
    </context></TS>""")
    assert ts_pairs(root) == [
        ("Open", "Otwórz", "Dialog", None),
        ("%n items", "%n rzecz", "Dialog", "singular"),
        ("%n items", "%n rzeczy wielu", "Dialog", "plural"),
        ("Open", "Otwórz", "Dialog", None),
    ], "Keep legacy eligibility/order; deduplication belongs to the writer"


@pytest.mark.parametrize("state", ["unfinished", "obsolete", "vanished"])
def test_ts_pairs_when_excluded_state_then_no_pair(state):
    root = ET.fromstring(
        f'<TS><context><name>X</name><message><source>A</source><translation type="{state}">B</translation></message></context></TS>'
    )
    assert ts_pairs(root) == [], "Excluded Qt targets cannot enter the memory"


def test_ts_pairs_when_no_context_or_single_plural_then_keep_legacy_shape():
    root = ET.fromstring(
        "<TS><context><name> </name><message><source>A</source><translation><numerusform>B</numerusform></translation></message></context></TS>"
    )
    assert ts_pairs(root) == [("A", "B", None, "singular")]
    assert ts_pairs(ET.fromstring("<TS/>")) == []


@pytest.mark.parametrize("fuzzy", [False, True])
def test_po_pairs_when_mixed_entries_then_preserve_context_plural_and_fuzzy_policy(
    fuzzy,
):
    catalog = polib.POFile()
    catalog.extend(
        [
            polib.POEntry(msgid="Open", msgstr="Otwórz", msgctxt="Menu"),
            polib.POEntry(msgid="Maybe", msgstr="Może", flags=["fuzzy"]),
            polib.POEntry(msgid="Old", msgstr="Stare", obsolete=True),
            polib.POEntry(msgid="Missing", msgstr=""),
            polib.POEntry(
                msgid="item",
                msgid_plural="items",
                msgstr_plural={0: "rzecz", 1: "rzeczy", 2: "rzeczy wielu"},
            ),
        ]
    )
    expected = [("Open", "Otwórz", "Menu", None)]
    if fuzzy:
        expected.append(("Maybe", "Może", None, None))
    expected += [
        ("item", "rzecz", None, "singular"),
        ("items", "rzeczy wielu", None, "plural"),
    ]
    assert po_pairs(catalog, fuzzy=fuzzy) == expected
    assert po_pairs(polib.POFile(), fuzzy=fuzzy) == []


def test_po_pairs_when_first_form_empty_then_keep_last_with_plural_source():
    catalog = polib.POFile()
    catalog.append(
        polib.POEntry(
            msgid="one", msgid_plural="many", msgstr_plural={0: "", 2: "wiele"}
        )
    )
    assert po_pairs(catalog, fuzzy=False) == [("many", "wiele", None, "plural")]
