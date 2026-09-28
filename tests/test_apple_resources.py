# this_file: tests/test_apple_resources.py
"""Apple resource extraction preserves values before application-specific pairing."""

import plistlib

import pytest

from vexy_localizzy.apple_resources import (
    flatten_value,
    parse_strings_text,
    resource_items,
)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "utf-16-be"])
def test_text_when_comments_quotes_and_duplicate_keys_then_preserve_values(encoding):
    text = r"""/* ignored */
"a" = "literal /* keep */ and // keep"; // ignored
"a" = "second"; "quote" = "say \"yes\"";
"unicode" = "\UD83D\UDE00 \U0105";
"space" = " leading\ntrailing ";
"""
    data = text.encode(encoding)
    if encoding == "utf-16-be":
        data = b"\xfe\xff" + data
    assert parse_strings_text(data) == [
        ("a", "literal /* keep */ and // keep"),
        ("a", "second"),
        ("quote", 'say "yes"'),
        ("unicode", "😀 ą"),
        ("space", " leading\ntrailing "),
    ]


@pytest.mark.parametrize(
    "data",
    [
        b'"a"="unterminated;',
        b'"a"="ok"; garbage!',
        b'"a"="ok"; /* unclosed',
        b'"a"=("list");',
        b'"a"="\xff";',
    ],
)
def test_text_when_malformed_then_refuse_partial_or_corrupted_result(data):
    with pytest.raises(ValueError):
        parse_strings_text(data)


@pytest.mark.parametrize("fmt", [plistlib.FMT_XML, plistlib.FMT_BINARY])
def test_resource_items_when_plist_then_retain_native_values_and_order(fmt):
    obj = {"second": "ą", "first": {"NSStringLocalizedFormatKey": "%#@n@"}}
    assert resource_items(plistlib.dumps(obj, fmt=fmt, sort_keys=False)) == list(
        obj.items()
    )
    with pytest.raises(ValueError, match="dictionary"):
        resource_items(plistlib.dumps(["wrong root"], fmt=fmt))


def test_resource_items_when_text_or_empty_then_return_ordered_pairs():
    assert resource_items(b'"x"="one"; "x"="two";') == [("x", "one"), ("x", "two")]
    assert resource_items(b"") == []
    assert parse_strings_text(b"// comment only") == []


def test_flatten_when_plural_then_keep_format_and_all_nonempty_forms():
    value = {
        "NSStringLocalizedFormatKey": "%#@n@",
        "n": {
            "NSStringFormatSpecTypeKey": "NSStringPluralRuleType",
            "NSStringFormatValueTypeKey": "d",
            "one": "%d item",
            "few": "%d items",
            "other": "%d things",
            "empty": "",
            "number": 3,
        },
    }
    assert list(flatten_value("key", value)) == [
        ("key", "%#@n@"),
        ("key|n|one", "%d item"),
        ("key|n|few", "%d items"),
        ("key|n|other", "%d things"),
    ]


@pytest.mark.parametrize(
    "device,expected", [("mac", "desktop"), ("iphone", "phone"), ("ipad", "fallback")]
)
def test_flatten_when_device_variants_then_use_selected_device_or_other(
    device, expected
):
    value = {
        "NSStringDeviceSpecificRuleType": {
            "mac": "desktop",
            "iphone": "phone",
            "other": "fallback",
        }
    }
    assert list(flatten_value("key", value, device=device)) == [("key", expected)]


@pytest.mark.parametrize(
    "value", ["", None, 3, [], {}, {"NSStringDeviceSpecificRuleType": []}]
)
def test_flatten_when_no_usable_text_then_empty(value):
    assert list(flatten_value("key", value)) == []
