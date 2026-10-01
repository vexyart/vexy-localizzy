# this_file: tests/test_review_workspace.py
"""A catalog is imported into a resumable review workspace; the source is never edited."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from vexy_localizzy.catalog import Catalog, Unit
from vexy_localizzy.formats import json_io, ts
from vexy_localizzy.review import server
from vexy_localizzy.review.workspace import prepare_workspace


def _catalog() -> Catalog:
    return Catalog(
        source_lang="en",
        target_lang="de",
        units=[
            Unit(
                key="menu.open",
                context="W",
                source="Open",
                state="translated",
                target="Öffnen",
            ),
            Unit(
                key="menu.close",
                context="W",
                source="Close",
                state="needs_review",
                target="Schliessen",
            ),
        ],
    )


def _client(source, **kwargs):
    config = (
        source
        if Path(source).suffix == ".toml"
        else prepare_workspace(source, **kwargs)
    )
    app = server.load_app(config, web_root=server.WEB_ROOT)
    return TestClient(app, base_url="http://127.0.0.1")


def _json_client(tmp_path, **kwargs):
    path = tmp_path / "de.json"
    if not path.exists():
        json_io.dump(_catalog(), path)
    return _client(path, **kwargs), path


def _edit(client, key="menu.open", target="Datei öffnen", action="draft"):
    revision = client.get("/api/catalogs/main").json()["revision"]
    return {
        "key": key,
        "revision": revision,
        "targets": {"scalar": target},
        "action": action,
    }


def test_workspace_when_json_imported_then_ui_and_summary_served(tmp_path):
    client, _ = _json_client(tmp_path)
    assert client.get("/").status_code == 200, "the packaged frontend must be served"
    summary = client.get("/api/catalogs").json()[0]
    assert summary["total"] == 2, summary
    assert summary["states"] == {"translated": 1, "needs_review": 1}, summary


def test_workspace_when_edit_saved_then_reopen_keeps_work_and_source(tmp_path):
    client, path = _json_client(tmp_path)
    original = path.read_bytes()
    edit = _edit(client)
    saved = client.post("/api/catalogs/main/edits", json=edit)
    assert saved.status_code == 200, saved.text
    assert saved.json()["units"][0]["target"] == "Datei öffnen"
    assert path.read_bytes() == original, "review must not edit the imported catalog"
    reopened, _ = _json_client(tmp_path)
    assert reopened.get("/api/catalogs/main").json() == saved.json(), "work survives"
    assert reopened.post("/api/catalogs/main/edits", json=edit).status_code == 409
    assert (Path(str(path) + ".review") / "catalog.json.review.jsonl").is_file()


def test_workspace_when_source_changed_then_refused_and_work_kept(tmp_path):
    client, path = _json_client(tmp_path)
    client.post("/api/catalogs/main/edits", json=_edit(client))
    saved = (Path(str(path) + ".review") / "catalog.json").read_bytes()
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="changed"):
        _json_client(tmp_path)
    assert (Path(str(path) + ".review") / "catalog.json").read_bytes() == saved


def test_workspace_when_ui_supplied_then_copied_and_reopened(tmp_path):
    ui = tmp_path / "dialog.ui"
    raw = b'<ui version="4.0"><class>Dialog</class><widget class="QDialog" name="Dialog"/></ui>'
    ui.write_bytes(raw)
    client, path = _json_client(tmp_path, ui_files=[ui])
    assets = client.get("/api/ui").json()
    assert len(assets) == 1 and client.get("/api/ui/" + assets[0]["id"]).content == raw
    reopened, _ = _json_client(tmp_path)
    assert reopened.get("/api/ui").json() == assets, "previews survive a reopen"
    configured = _client(Path(str(path) + ".review") / "review.toml")
    assert (
        configured.get("/api/catalogs/main").json()
        == client.get("/api/catalogs/main").json()
    )


def test_workspace_when_directory_unrecognized_then_nothing_overwritten(tmp_path):
    workspace = tmp_path / "existing"
    workspace.mkdir()
    marker = workspace / "important.txt"
    marker.write_text("keep")
    with pytest.raises(ValueError, match="workspace"):
        _json_client(tmp_path, workspace=workspace)
    assert list(workspace.iterdir()) == [marker] and marker.read_text() == "keep"


def test_workspace_when_preview_not_ui_then_nothing_created(tmp_path):
    workspace = tmp_path / "review"
    bad = tmp_path / "image.png"
    bad.write_bytes(b"image")
    with pytest.raises(ValueError, match=".ui"):
        _json_client(tmp_path, workspace=workspace, ui_files=[bad])
    assert not workspace.exists(), "a refused import leaves no partial workspace"


def test_workspace_when_lock_hardlinked_then_source_preserved(tmp_path):
    source = tmp_path / "de.ts"
    raw = b'<TS language="de"><context><name>C</name><message><source>Open</source></message></context></TS>'
    source.write_bytes(raw)
    workspace = tmp_path / "work"
    Path(str(workspace) + ".setup.lock").hardlink_to(source)
    with pytest.raises(ValueError, match="lock"):
        prepare_workspace(source, workspace=workspace)
    assert source.read_bytes() == raw, "setup locking must never truncate an alias"
    assert not workspace.exists()


def test_workspace_when_suffix_unsupported_then_value_error(tmp_path):
    source = tmp_path / "de.po"
    source.write_text('msgid "a"\nmsgstr "b"\n')
    with pytest.raises(ValueError, match="TS, canonical JSON"):
        prepare_workspace(source)


def test_workspace_when_ts_reviewed_then_native_slots_and_metadata_survive(tmp_path):
    source = tmp_path / "pl.ts"
    raw = b"""<?xml version="1.0" encoding="utf-8"?>
<TS version="2.1" language="pl" sourcelanguage="en"><context><name>Dialog</name>
<message id="count" numerus="yes"><location filename="dialog.ui" line="12"/>
<source>%n points</source><extracomment>Keep %n.</extracomment>
<translation type="unfinished"><numerusform>%n punkt</numerusform>
<numerusform>%n punkty</numerusform><numerusform>%n punktow</numerusform></translation>
</message></context></TS>"""
    source.write_bytes(raw)
    client = _client(source)
    initial = client.get("/api/catalogs/main").json()
    unit = initial["units"][0]
    assert set(unit["slots"]) == {"0", "1", "2"}, unit["slots"]
    edit = {
        "key": unit["key"],
        "revision": initial["revision"],
        "targets": {"0": "%n punkt", "1": "%n punkty", "2": "%n punktów"},
        "action": "approve",
    }
    missing = {**edit, "targets": {"0": "%n punkt"}}
    assert client.post("/api/catalogs/main/edits", json=missing).status_code == 422
    broken = {**edit, "targets": {**edit["targets"], "2": "punktów"}}
    assert client.post("/api/catalogs/main/edits", json=broken).status_code == 422
    saved = client.post("/api/catalogs/main/edits", json=edit)
    assert saved.status_code == 200, saved.text
    exported = client.get("/api/catalogs/main/export.ts")
    assert exported.status_code == 200, exported.text
    before, after = etree.fromstring(raw), etree.fromstring(exported.content)
    assert [n.text for n in after.findall(".//numerusform")] == list(
        edit["targets"].values()
    )
    for document in (before, after):
        node = document.find(".//translation")
        node.getparent().remove(node)
    assert etree.tostring(before) == etree.tostring(after), (
        "non-target XML must survive"
    )
    assert source.read_bytes() == raw, "the source catalog is never edited"


@pytest.mark.parametrize(
    "translation",
    [
        "",
        '<translation type="unfinished"/>',
        '<translation type="unfinished"><numerusform>%n punkt</numerusform></translation>',
    ],
)
def test_workspace_when_plural_incomplete_then_missing_slots_editable(
    tmp_path, translation
):
    source = tmp_path / "pl.ts"
    raw = (
        '<TS language="pl" sourcelanguage="en"><context><name>C</name>'
        '<message numerus="yes"><source>%n points</source>'
        + translation
        + "</message></context></TS>"
    ).encode()
    source.write_bytes(raw)
    client = _client(source)
    catalog = client.get("/api/catalogs/main").json()
    unit = catalog["units"][0]
    assert set(unit["slots"]) == {"0", "1", "2"}, (
        "missing native forms must be editable"
    )
    assert unit["slots"]["0"] == ("%n punkt" if "numerusform" in translation else "")
    edit = {
        "key": unit["key"],
        "revision": catalog["revision"],
        "action": "approve",
        "targets": {"0": "%n punkt", "1": "%n punkty", "2": "%n punktów"},
    }
    assert client.post("/api/catalogs/main/edits", json=edit).status_code == 200
    exported = client.get("/api/catalogs/main/export.ts")
    assert len(etree.fromstring(exported.content).findall(".//numerusform")) == 3
    assert source.read_bytes() == raw


@pytest.mark.parametrize(
    "before,after", [("unfinished", "vanished"), ("vanished", "needs_review")]
)
def test_workspace_when_canonical_state_differs_then_current_state_prepared(
    tmp_path, before, after
):
    source = tmp_path / "source.ts"
    source.write_text(
        '<TS language="pl"><context><name>C</name>'
        '<message numerus="yes"><source>%n points</source><translation type="'
        + before
        + '"><numerusform>%n punkt</numerusform></translation></message>'
        '<message numerus="yes"><source>%n lines</source><translation type="unfinished"/></message>'
        "</context></TS>"
    )
    catalog = ts.load(source)
    units = list(catalog.units)
    units[0] = units[0].model_copy(update={"state": after})
    canonical = tmp_path / "input.json"
    json_io.dump(catalog.model_copy(update={"units": units}), canonical)
    original = canonical.read_bytes()
    exported = _client(canonical).get("/api/catalogs/main/export.ts")
    assert exported.status_code == 200, exported.text
    (tmp_path / "after.ts").write_bytes(exported.content)
    result = ts.load(tmp_path / "after.ts")
    assert len(result.units[0].plural.forms) == (1 if after == "vanished" else 3)
    assert result.units[0].plural.forms["0"] == "%n punkt"
    assert len(result.units[1].plural.forms) == 3, "active plurals get every slot"
    assert canonical.read_bytes() == original


@pytest.mark.parametrize("port", [0, 65536, True])
def test_serve_when_port_invalid_then_no_workspace_created(tmp_path, port):
    source = tmp_path / "missing.ts"
    with pytest.raises(ValueError, match="Port"):
        server.serve(str(source), port=port)
    assert not Path(str(source) + ".review").exists()


def test_serve_when_toml_given_with_workspace_options_then_refused(
    tmp_path, monkeypatch
):
    config = tmp_path / "review.toml"
    config.write_text('[catalogs]\nmain = "catalog.json"\n')
    with pytest.raises(ValueError, match="inside the review TOML"):
        server.serve(str(config), workspace="elsewhere")
