# this_file: tests/test_printf_qa.py
"""Real GNU gettext validation rather than a second printf grammar."""

import shutil

import pytest

from vexy_localizzy.qa.printf import printf_error
from vexy_localizzy.qa.text import TextPolicy, check_text


@pytest.mark.skipif(
    shutil.which("msgfmt") is None, reason="Native GNU gettext is required"
)
@pytest.mark.parametrize(
    "source,target,valid",
    [
        ("%s: %d", "%2$d: %1$s", True),
        ("%s: %d", "%d: %s", False),
        ("%*.*f", "%3$*1$.*2$f", True),
        ("%*.*f", "%f", False),
        ("%lld", "%d", False),
        ("%s", "%s %d", False),
        ("%s 100%%", "%s 100%%", True),
    ],
)
def test_printf_when_native_argument_contract_checked_then_expected_result(
    source, target, valid
):
    assert (printf_error(source, target) is None) == valid


def test_printf_when_executable_missing_then_never_report_success(tmp_path):
    with pytest.raises(FileNotFoundError):
        check_text(
            "%s",
            "%d",
            policy=TextPolicy(
                placeholder_styles=("printf",), msgfmt=str(tmp_path / "missing")
            ),
        )


@pytest.mark.skipif(
    shutil.which("msgfmt") is None, reason="Native GNU gettext is required"
)
@pytest.mark.parametrize("target", ["Koszt %d", "Koszt %d %"])
def test_printf_when_source_format_invalid_then_never_accept_skipped_native_check(
    target,
):
    assert printf_error("Cost %s %", target) is not None
