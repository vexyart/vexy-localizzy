# this_file: tests/test_review_api.py
"""HTTP review flows against real journaled files and revision/QA boundaries."""

from fastapi.testclient import TestClient
from review_fixtures import edit, store

from vexy_localizzy.review.api import create_app


def client(tmp_path):
    saved = store(tmp_path)
    (tmp_path / "sample.ui").write_text(
        '<ui version="4.0"><class>Menu</class><widget class="QDialog" name="Dialog"/></ui>'
    )
    app = create_app(saved, ui_files={"sample": "sample.ui"})
    return TestClient(app, base_url="http://127.0.0.1"), saved


def test_api_when_editing_then_validate_save_reopen_and_conflict(tmp_path):
    api, saved = client(tmp_path)
    listing = api.get("/api/catalogs").json()
    assert listing[0]["id"] == "main"
    current = api.get("/api/catalogs/main").json()
    assert "document" not in current
    assert current["units"][0]["slots"] == {"scalar": "Otwórz %1"}
    request = edit(current["revision"]).model_dump()
    checked = api.post("/api/catalogs/main/validate", json=request)
    assert checked.status_code == 200 and checked.json()["findings"] == []
    assert saved.open("main").revision == current["revision"]
    changed = api.post("/api/catalogs/main/edits", json=request)
    assert changed.status_code == 200, changed.text
    assert api.get("/api/catalogs/main").json() == changed.json()
    assert api.post("/api/catalogs/main/edits", json=request).status_code == 409
    assert saved.open("main").catalog.units[0].target == request["targets"]["scalar"]


def test_api_when_invalid_or_cross_origin_then_never_write(tmp_path):
    api, saved = client(tmp_path)
    before = saved.open("main")
    request = edit(before.revision, "Wrong").model_dump()
    for endpoint in ("validate", "edits"):
        assert (
            api.post(f"/api/catalogs/main/{endpoint}", json=request).status_code == 422
        )
    request = edit(before.revision).model_dump()
    assert (
        api.post(
            "/api/catalogs/main/edits",
            json=request,
            headers={"Origin": "https://unrelated.example"},
        ).status_code
        == 403
    )
    assert (
        api.post(
            "/api/catalogs/main/edits", json={**request, "source": "Overwritten"}
        ).status_code
        == 422
    )
    assert saved.open("main") == before


def test_api_when_opening_assets_or_suggestions_then_only_configured_data(tmp_path):
    api, _ = client(tmp_path)
    assert api.get("/api/ui").json() == [{"id": "sample", "name": "sample.ui"}]
    assert "<ui" in api.get("/api/ui/sample").text
    assert api.get("/api/ui/unknown").status_code == 404
    assert api.get("/api/catalogs/unknown").status_code == 404
    assert (
        api.get("/api/catalogs/main/suggestions", params={"key": "open"}).json() == []
    )
    assert (
        api.get("/api/catalogs/main/suggestions", params={"key": "missing"}).status_code
        == 404
    )


def test_api_when_exporting_then_native_ts_contains_saved_target(tmp_path):
    from vexy_localizzy.formats import json_io, ts

    api, saved = client(tmp_path)
    raw = b'<TS language="pl" sourcelanguage="en"><context><name>Menu</name><message id="open"><source>Open %1</source><translation>Otworz %1</translation></message></context></TS>'
    path = tmp_path / "input.ts"
    path.write_bytes(raw)
    json_io.dump(ts.load(path), tmp_path / "catalog.json")
    current = saved.open("main")
    request = edit(current.revision).model_copy(
        update={"key": current.catalog.units[0].key}
    )
    assert (
        api.post("/api/catalogs/main/edits", json=request.model_dump()).status_code
        == 200
    )
    exported = api.get("/api/catalogs/main/export.ts")
    assert exported.status_code == 200
    assert "attachment" in exported.headers["content-disposition"]
    output = tmp_path / "export.ts"
    output.write_bytes(exported.content)
    assert ts.load(output).units[0].target == "Otwórz plik %1"
