# this_file: tests/test_move_modules.py
# move-modules: skip
"""The module-move script rewrites imports correctly and idempotently."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "move_modules.py"
spec = importlib.util.spec_from_file_location("move_modules", SCRIPT)
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)

ALL = {old: new for group in mm.GROUPS.values() for old, new in group.items()}
DIRS = {old: new for group in mm.DIR_MOVES.values() for old, new in group.items()}

CASES = [
    (
        "from vexy_localizzy.qa import TextPolicy",
        "from vexy_localizzy.qa.text import TextPolicy",
    ),
    (
        'patch("vexy_localizzy.qa.check_text")',
        'patch("vexy_localizzy.qa.text.check_text")',
    ),
    (
        "from vexy_localizzy.qa.catalog import x",
        "from vexy_localizzy.qa.catalog import x",
    ),
    (
        "from vexy_localizzy.qa_catalog import x",
        "from vexy_localizzy.qa.catalog import x",
    ),
    (
        "from vexy_localizzy.corpus_identity import x",
        "from vexy_localizzy.corpus.identity import x",
    ),
    (
        "from vexy_localizzy.corpus import Corpus",
        "from vexy_localizzy.corpus.store import Corpus",
    ),
    (
        "from vexy_localizzy.formats.tmx import x",
        "from vexy_localizzy.formats.tmx import x",
    ),
    (
        "from vexy_localizzy.tmx import read_tmx",
        "from vexy_localizzy.memory.tmx_read import read_tmx",
    ),
    (
        "from vexy_localizzy.tmx_writer import w",
        "from vexy_localizzy.memory.tmx_write import w",
    ),
    ("from vexy_localizzy.cli import main", "from vexy_localizzy.cli import main"),
    (
        "from vexy_localizzy.catalog import Unit",
        "from vexy_localizzy.catalog import Unit",
    ),
    (
        "    from vexy_localizzy import cli_tm, catalog  # note",
        "    from vexy_localizzy import catalog\n    from vexy_localizzy.cli import tm as cli_tm  # note",
    ),
    (
        "from vexy_localizzy import review_server",
        "from vexy_localizzy.review import server as review_server",
    ),
    (
        "import vexy_localizzy.exporter as exporter",
        "import vexy_localizzy.corpus.exporter as exporter",
    ),
    (
        "# this_file: src/vexy_localizzy/qa.py",
        "# this_file: src/vexy_localizzy/qa/text.py",
    ),
    (
        "# this_file: src/vexy_localizzy/cli.py",
        "# this_file: src/vexy_localizzy/cli/__init__.py",
    ),
    (
        "outDir: '../src/vexy_localizzy/review_web'",
        "outDir: '../src/vexy_localizzy/review/web'",
    ),
    (
        "from vexy_localizzy.classification_run import run",
        "from vexy_localizzy.experimental.classification_run import run",
    ),
]


@pytest.mark.parametrize(("before", "after"), CASES)
def test_rewrite_text_when_old_path_then_new_path(before: str, after: str) -> None:
    assert mm.rewrite_text(before, ALL, DIRS) == after, before


@pytest.mark.parametrize(("before", "after"), CASES)
def test_rewrite_text_when_run_twice_then_unchanged(before: str, after: str) -> None:
    once = mm.rewrite_text(before, ALL, DIRS)
    assert mm.rewrite_text(once, ALL, DIRS) == once, f"second pass changed {once!r}"


def test_rewrite_text_when_parenthesized_from_import_then_error() -> None:
    with pytest.raises(ValueError, match="parenthesized"):
        mm.rewrite_text("from vexy_localizzy import (\n    qa,\n)\n", ALL, DIRS)


def test_stub_text_when_rendered_then_aliases_new_module() -> None:
    text = mm.stub_text("vexy_localizzy.qa_tokens", "vexy_localizzy.qa.tokens")
    assert mm.MARKER in text
    assert "importlib.import_module(_NEW)" in text
    assert "DeprecationWarning" in text


def test_groups_when_listed_then_no_old_path_moves_twice() -> None:
    olds = [old for group in mm.GROUPS.values() for old in group]
    assert len(olds) == len(set(olds)), "an old path appears in two groups"
