# this_file: tests/test_moved_module_aliases.py
# move-modules: skip
"""Old module paths kept as deprecated aliases resolve to the moved modules."""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "move_modules", ROOT / "scripts" / "move_modules.py"
)
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)

MOVES = {old: new for group in mm.GROUPS.values() for old, new in group.items()}
LIVE = sorted(
    old
    for old in mm.STUBS
    if (ROOT / "src" / mm.module_file(old)).is_file()
    and mm.MARKER in (ROOT / "src" / mm.module_file(old)).read_text()
)


def test_aliases_when_moves_applied_then_some_exist() -> None:
    assert LIVE, "no alias stub found; the qa group should have written two"


@pytest.mark.parametrize("old", LIVE)
def test_alias_when_imported_then_same_module_and_deprecation_warning(
    old: str,
) -> None:
    new = importlib.import_module(MOVES[old])
    sys.modules.pop(old, None)
    with pytest.warns(DeprecationWarning, match="moved to"):
        aliased = importlib.import_module(old)
    assert aliased is new, f"{old} should alias {MOVES[old]}"
    assert sys.modules[old] is new


def test_alias_when_monkeypatched_by_old_dotted_path_then_new_module_sees_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = "vexy_localizzy.qa_tokens"
    new = importlib.import_module(MOVES[old])
    sys.modules.pop(old, None)
    with pytest.warns(DeprecationWarning):
        importlib.import_module(old)
    sentinel = object()
    monkeypatch.setattr(f"{old}.check_tokens", sentinel)
    assert new.check_tokens is sentinel


def test_qa_package_when_imported_then_reexports_text_entry_points() -> None:
    from vexy_localizzy.qa import TextPolicy, check_text, text, validate_batch

    assert (TextPolicy, check_text, validate_batch) == (
        text.TextPolicy,
        text.check_text,
        text.validate_batch,
    )


def test_cli_package_when_imported_then_submodules_not_shadowed() -> None:
    import types

    import vexy_localizzy.cli as cli

    for name in ("translate", "upgrade", "tm"):
        assert isinstance(getattr(cli, name), types.ModuleType), name
    assert cli.COMMANDS["translate"] is cli.translate.translate
    assert cli.COMMANDS["upgrade"] is cli.upgrade.upgrade
    assert cli.COMMANDS["tm"] is cli.tm.TM_COMMANDS


@pytest.mark.parametrize(
    "statement",
    [
        "from vexy_localizzy.corpus import Corpus",
        "from vexy_localizzy.corpus import exporter, store",
        "from vexy_localizzy.qa import TextPolicy, check_text, validate_batch",
    ],
)
def test_package_named_like_old_module_when_imported_fresh_then_works(
    statement: str,
) -> None:
    import subprocess

    result = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c", statement],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_corpus_package_when_unknown_name_then_attribute_error() -> None:
    import vexy_localizzy.corpus as corpus

    with pytest.raises(AttributeError):
        corpus.NotAThing  # noqa: B018
    from vexy_localizzy.corpus.store import Corpus

    assert corpus.Corpus is Corpus
