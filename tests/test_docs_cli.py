# this_file: tests/test_docs_cli.py
"""docs/cli.md matches the current ``localizzy … --help`` output."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "gen_cli_docs.py"
spec = importlib.util.spec_from_file_location("gen_cli_docs", SCRIPT)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def test_cli_doc_when_generated_then_matches_committed_file() -> None:
    assert gen.DOC.read_text(encoding="utf-8") == gen.render(), (
        "docs/cli.md is stale; run: uv run scripts/gen_cli_docs.py"
    )


def test_cli_doc_when_rendered_then_covers_every_command() -> None:
    text = gen.render()
    for path in gen.command_paths(gen.COMMANDS):
        assert f"## localizzy {' '.join(path)}\n" in text, path
    assert "INFO: Showing help" not in text
