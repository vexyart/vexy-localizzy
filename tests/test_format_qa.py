# this_file: tests/test_format_qa.py
"""translate's QA follows each catalog format's own placeholder syntax."""

import shutil

import pytest

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.conversion import load_any
from vexy_localizzy.qa.formats import format_policy
from vexy_localizzy.qa.text import TextPolicy, check_text
from vexy_localizzy.translate.run import translate_file

needs_msgfmt = pytest.mark.skipif(
    shutil.which("msgfmt") is None, reason="Native GNU gettext is required"
)

PO = """msgid ""
msgstr ""
"Language: de\\n"
"Content-Type: text/plain; charset=UTF-8\\n"

#, c-format
msgid "Delete %s files"
msgstr ""

#, python-brace-format
msgid "Hello {name}"
msgstr ""

msgid "100% done"
msgstr ""
"""

MEMORY = """<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4"><header creationtool="t" creationtoolversion="1"
segtype="phrase" o-tmf="tmx" adminlang="en" srclang="en" datatype="plaintext"/>
<body>{units}</body></tmx>
"""


def _tu(source: str, target: str) -> str:
    return (
        f'<tu tuid="{source}"><prop type="x-context"></prop>'
        f'<tuv xml:lang="en"><seg>{source}</seg></tuv>'
        f'<tuv xml:lang="de"><seg>{target}</seg></tuv></tu>'
    )


def test_text_policy_when_default_then_serialized_identity_unchanged():
    assert TextPolicy().model_dump_json() == (
        '{"placeholder_styles":["qt"],"markup":"auto","accelerators":true,'
        '"max_length":null,"msgfmt":"msgfmt"}'
    ), "TS cache validation identities must not change"


def test_format_policy_when_po_then_styles_follow_entry_flags(tmp_path):
    path = tmp_path / "de.po"
    path.write_text(PO, encoding="utf-8")
    catalog = load_any(path)
    policy = format_policy(catalog)
    by_source = {u.source: policy.styles_for(u.key) for u in catalog.units}
    assert by_source == {
        "Delete %s files": ("printf",),
        "Hello {name}": ("python_brace",),
        "100% done": (),
    }, "unflagged entries get no placeholder check, as with msgfmt"
    assert "unit_styles_sha256" in policy.model_dump_json()


def test_format_policy_when_ts_then_qt_default():
    catalog = Catalog(source_lang="en", origin_format="ts")
    assert format_policy(catalog) == TextPolicy()


def test_format_policy_when_android_then_printf_only_for_format_strings():
    units = [
        Unit(key="a", context="", source="Delete %1$s?"),
        Unit(key="b", context="", source="100% done"),
    ]
    policy = format_policy(
        Catalog(source_lang="en", origin_format="android", units=units)
    )
    assert policy.styles_for("a") == ("printf",)
    assert policy.styles_for("b") == ()


def test_check_text_when_i18next_token_dropped_then_mismatch():
    policy = TextPolicy(placeholder_styles=("i18next",))
    found = {f.rule_id for f in check_text("Hi {{name}}", "Hallo", policy=policy)}
    assert "PH-MISMATCH" in found
    assert not check_text("Hi {{ name }}", "Hallo {{name}}", policy=policy)


def _po_run(tmp_path, *pairs: tuple[str, str]):
    catalog = tmp_path / "de.po"
    catalog.write_text(PO, encoding="utf-8")
    memory = tmp_path / "m.tmx"
    memory.write_text(
        MEMORY.format(units="".join(_tu(s, t) for s, t in pairs)), encoding="utf-8"
    )
    out = tmp_path / "out.po"
    report = translate_file(catalog, target="de", out=out, direct_memories=[memory])
    return report, out.read_text(encoding="utf-8")


def test_translate_file_when_po_brace_placeholder_lost_then_memory_hit_rejected(
    tmp_path,
):
    report, text = _po_run(tmp_path, ("Hello {name}", "Hallo"))
    assert report.counts["memory_rejected_qa"] == 1, report.counts
    assert 'msgstr "Hallo"' not in text


@needs_msgfmt
def test_translate_file_when_po_c_format_placeholder_lost_then_memory_hit_rejected(
    tmp_path,
):
    report, text = _po_run(
        tmp_path, ("Delete %s files", "Dateien löschen"), ("100% done", "100% fertig")
    )
    assert report.counts["memory_rejected_qa"] == 1, report.counts
    assert 'msgstr "Dateien löschen"' not in text
    assert 'msgstr "100% fertig"' in text, "an unflagged entry is not printf-checked"
    assert not report.ready


@pytest.mark.parametrize(
    ("source", "styles"),
    [
        ("Hello {name}", ("python_brace",)),
        ("Hi {{name}}", ("i18next",)),
        ("Open %1", ("qt",)),
        ("Delete %s", ("printf",)),
        ("{count, plural, one {x} other {y}}", ()),
        ("Plain text", ()),
    ],
)
def test_format_policy_when_xliff_then_styles_detected_per_unit(source, styles):
    from vexy_localizzy.catalog import detect_placeholders

    unit = Unit(
        key="k", context="", source=source, placeholders=detect_placeholders(source)
    )
    policy = format_policy(
        Catalog(source_lang="en", origin_format="xliff", units=[unit])
    )
    assert policy.styles_for("k") == styles, source
