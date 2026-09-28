# this_file: tests/classification_run_fixtures.py
"""Synthetic frozen inputs and deterministic three-model transport for run tests."""

import json
from pathlib import Path

from vexy_localizzy.provider_errors import ModelResponse


def write_inputs(path: Path, count: int = 201) -> Path:
    metadata = {
        "type": "metadata",
        "version": 1,
        "entries": count,
        "source_snapshot": "a" * 64,
        "entry_map_sha256": "b" * 64,
        "coverage": {"pl": count} if count else {},
    }
    path.write_text(
        json.dumps(metadata)
        + "\n"
        + "".join(
            json.dumps({"id": i + 1, "text": f"Source {i}", "locales": ["pl"]}) + "\n"
            for i in range(count)
        )
    )
    return path


def response(model: str, _prompt: str, payload: str) -> ModelResponse:
    entries = json.loads(payload)["entries"]
    return ModelResponse("\n".join(f"{e['number']} A" for e in entries), model)


def options(tmp_path: Path) -> dict:
    return {
        "cache_path": tmp_path / "responses.sqlite",
        "models": ["one", "two", "three"],
        "prompt": "Synthetic classification rubric",
        "request": response,
        "endpoint_identity": "https://example.test/v1",
        "workers": 1,
    }
