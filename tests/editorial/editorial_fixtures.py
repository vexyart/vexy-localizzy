# this_file: tests/editorial/editorial_fixtures.py
"""Synthetic TS catalogs, candidate records, glossaries and a fake review endpoint."""

import json
from pathlib import Path

from vexy_localizzy.editorial.apply import apply_ts
from vexy_localizzy.editorial.commit import commit_files
from vexy_localizzy.editorial.json_files import apply_json
from vexy_localizzy.formats.ts import load
from vexy_localizzy.translate.provider_errors import ModelResponse


def ts(messages: list[str], language: str = "fr_FR", context: str = "Main") -> str:
    """A minimal TS file; ``messages`` are XML snippets of <message> bodies."""
    body = "".join(f"<message>{m}</message>" for m in messages)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
        f'<TS version="2.1" language="{language}" sourcelanguage="en">\n'
        f"<context><name>{context}</name>{body}</context>\n</TS>\n"
    )


def candidate(key: str, source, before, revised, **extra) -> dict:
    return {
        "id": key,
        "source": source,
        "before": before,
        "revised": revised,
        "reason": "test",
        "family": "accuracy",
        "severity": "major",
        "model": "test-model",
        **extra,
    }


def run_ts(catalog: Path, changes, language: str, *, dry_run=False, finish=False):
    """``apply_ts`` and, unless ``dry_run``, write the catalog; return the outcome."""
    result = apply_ts(catalog, changes, language, finish=finish)
    if result.render and not dry_run:
        commit_files([(catalog, result.render)])
    return result.outcome


def run_json(target: Path, source: Path, changes, language: str, *, dry_run=False):
    """``apply_json`` and, unless ``dry_run``, write the file; return the outcome."""
    result = apply_json(target, source, changes, language)
    if result.render and not dry_run:
        commit_files([(target, result.render)])
    return result.outcome


def units(path: Path) -> dict:
    return {u.key: u for u in load(path).units}


def write_json(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def write_candidates(path: Path, *records: list[dict], model: str = "m") -> Path:
    """A candidates JSONL file with one record per list of corrections."""
    lines = [
        json.dumps({"batch": f"b{n}", "model": model, "corrections": corrections})
        for n, corrections in enumerate(records)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def glossary(path: Path, *pairs: tuple[str, str], lang: str = "fr") -> Path:
    """A TMX glossary of approved terms."""
    tus = "".join(
        f'<tu tuid="term:{s}"><prop type="x-status">approved</prop>'
        f'<tuv xml:lang="en"><seg>{s}</seg></tuv>'
        f'<tuv xml:lang="{lang}"><seg>{t}</seg></tuv></tu>'
        for s, t in pairs
    )
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><tmx version="1.4">'
        '<header creationtool="t" creationtoolversion="1" segtype="sentence" '
        'o-tmf="t" adminlang="en" srclang="en" datatype="plaintext"/>'
        f"<body>{tus}</body></tmx>",
        encoding="utf-8",
    )
    return path


class FakeEndpoint:
    """Records every (system, user) pair; answers with ``reply(user)`` or raises."""

    def __init__(self, reply=lambda user: "<output>[]</output>", fail: int = 0):
        self.calls: list[tuple[str, str]] = []
        self.reply = reply
        self.fail = fail

    def __call__(self, system: str, user: str) -> ModelResponse:
        self.calls.append((system, user))
        if self.fail:
            self.fail -= 1
            raise RuntimeError("provider down")
        return ModelResponse(self.reply(user), "fake-model")

    def items(self, call: int = 0) -> list[dict]:
        """The batch items sent in call ``call``."""
        return json.loads(self.calls[call][1].split("Items:\n", 1)[1])
