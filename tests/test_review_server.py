# this_file: tests/test_review_server.py
"""Exercise shipped configuration and synthetic workspace against the real API."""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vexy_localizzy.review_server import load_app


def test_example_when_created_then_native_states_suggestions_and_forms_are_usable(
    tmp_path,
):
    example = Path(__file__).resolve().parents[1] / "examples/review_sample.py"
    workspace = tmp_path / "review"
    subprocess.run(
        [sys.executable, str(example), str(workspace)], check=True, capture_output=True
    )
    client = TestClient(
        load_app(workspace / "review.toml"), base_url="http://localhost"
    )
    catalog = client.get("/api/catalogs/sample").json()
    assert catalog["total"] == 8 and catalog["approved"] == 2
    assert catalog["units"][0]["state"] == "needs_review"
    assert catalog["units"][5]["slots"] == {
        "0": "%n element",
        "1": "%n elementy",
        "2": "%n elementów",
    }
    assert (
        client.get(
            "/api/catalogs/sample/suggestions", params={"key": "id:open"}
        ).json()[0]["provenance"]
        == "Memory · sample:1"
    )
    assert client.get("/api/ui/sample").status_code == 200
    assert client.get("/api/catalogs/sample/export.ts").status_code == 200
    before = (workspace / "catalog.json").read_bytes()
    repeat = subprocess.run(
        [sys.executable, str(example), str(workspace)], capture_output=True
    )
    assert repeat.returncode != 0, "Sample generation must never overwrite review edits"
    assert (workspace / "catalog.json").read_bytes() == before


@pytest.mark.parametrize("setting", ["extra = true", 'suggestions = "../outside.json"'])
def test_config_when_unknown_or_outside_root_then_rejected(tmp_path, setting):
    root = tmp_path / "workspace"
    root.mkdir()
    (tmp_path / "outside.json").write_text("{}")
    config = root / "review.toml"
    config.write_text(setting + "\n[catalogs]\n")
    with pytest.raises(ValueError):
        load_app(config)
