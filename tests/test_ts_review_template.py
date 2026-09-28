# this_file: tests/test_ts_review_template.py
"""Review preparation may add missing positions but never discard translations."""

import pytest
from lxml import etree

from vexy_localizzy.formats import ts
from vexy_localizzy.formats.ts_template import prepare_review


@pytest.mark.parametrize("count", [0, 1, 3])
def test_review_when_forms_incomplete_then_keep_existing_and_allow_export(
    tmp_path, count
):
    forms = (
        '<numerusform variants="yes" extra="keep"><lengthvariant>%n Punkt</lengthvariant><lengthvariant>%n P.</lengthvariant></numerusform>'
        * count
    )
    raw = (
        '<TS language="pl"><context><name>C</name><message numerus="yes"><source>%n points</source><translation extra="keep">'
        + forms
        + "</translation></message></context></TS>"
    ).encode()
    result = prepare_review(raw, plural_count=3)
    unit = result.units[0]
    assert len(unit.plural.forms) == 3
    for i in range(count):
        assert unit.plural.forms[str(i)] == "%n Punkt"
        assert unit.plural.variants[str(i)] == ["%n Punkt", "%n P."]
    if count == 3:
        assert result.document.content == raw, "Complete documents stay byte-identical"
    else:
        assert unit.state == "untranslated"
    output = tmp_path / "prepared.ts"
    ts.dump(result, output)
    assert len(etree.fromstring(output.read_bytes()).findall(".//numerusform")) == 3
    assert (
        etree.fromstring(output.read_bytes()).find(".//translation").get("extra")
        == "keep"
    )


@pytest.mark.parametrize(
    "content",
    [
        "<numerusform/><numerusform/><numerusform/><numerusform/>",
        "<extra>keep</extra>",
        "keep",
    ],
)
def test_review_when_preparation_would_lose_data_then_reject(content):
    raw = (
        '<TS language="pl"><context><name>C</name><message numerus="yes"><source>%n points</source><translation>'
        + content
        + "</translation></message></context></TS>"
    ).encode()
    with pytest.raises(ValueError):
        prepare_review(raw, plural_count=3)


@pytest.mark.parametrize("count", [0, 7, True])
def test_review_when_count_invalid_then_reject(count):
    with pytest.raises(ValueError, match="plural_count"):
        prepare_review(b"", plural_count=count)
