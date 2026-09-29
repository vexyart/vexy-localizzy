# this_file: tests/sourcefix/test_workflow.py
"""English edits go upstream without erasing foreign translations or drafts."""

from pathlib import Path

import pytest
from lxml import etree

from vexy_localizzy.sourcefix import apply, prepare


def catalog(path, messages, language="en_US"):
    root = etree.Element("TS", version="2.1", language=language, sourcelanguage="en_US")
    context = etree.SubElement(root, "context")
    etree.SubElement(context, "name").text = "Window"
    for source, filename, line, target in messages:
        msg = etree.SubElement(context, "message")
        etree.SubElement(msg, "location", filename=filename, line=str(line))
        etree.SubElement(msg, "source").text = source
        etree.SubElement(msg, "translation").text = target
    path.write_bytes(
        etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="utf-8")
    )


def edit(path, old="Old", new="New", finished=True):
    tree = etree.parse(str(path))
    msg = next(m for m in tree.findall(".//message") if m.findtext("source") == old)
    target = msg.find("translation")
    target.text = new
    target.attrib.clear()
    if not finished:
        target.set("type", "unfinished")
    tree.write(str(path), xml_declaration=True, encoding="utf-8")


@pytest.fixture
def project(tmp_path, monkeypatch):
    folder = tmp_path / "i18n"
    folder.mkdir()
    code = tmp_path / "window.cpp"
    code.write_text('void Window::f() { tr("Old"); }\n')
    en, de, mirror = [
        folder / name for name in ("app_en.ts", "app_de.ts", "app_en_tofix.ts")
    ]
    catalog(en, [("Old", "../window.cpp", 1, "")])
    catalog(de, [("Old", "../window.cpp", 1, "Alt")], "de_DE")
    prepare(str(en), str(mirror), str(tmp_path))
    # Unit workflow tests isolate the external extractor. Native Qt has its own
    # integration test, so these failure/rollback contracts work without Qt.
    from vexy_localizzy.sourcefix.catalog import Catalog

    monkeypatch.setattr(
        "vexy_localizzy.sourcefix.source.current_locations",
        lambda paths, root, tool: Catalog(en).locations(),
    )
    monkeypatch.setattr("vexy_localizzy.sourcefix.refresh.rebuild", lambda *args: None)
    return tmp_path, code, en, de, mirror


def run(project, **kwargs):
    root, _, en, _, mirror = project
    return apply(str(mirror), str(en), str(root), **kwargs)


def test_prepare_when_run_twice_then_preserves_drafts(project):
    root, _, en, _, mirror = project
    msg = etree.parse(str(mirror)).find(".//message")
    assert msg.findtext("translation") == "Old"
    assert msg.find("translation").get("type") == "unfinished"
    edit(mirror, new="Draft", finished=False)
    before = mirror.read_bytes()
    with pytest.raises(FileExistsError):
        prepare(str(en), str(mirror), str(root))
    assert mirror.read_bytes() == before, "Preparation must never discard edits"


def test_apply_when_finished_then_updates_all_and_is_idempotent(project):
    _, code, en, de, mirror = project
    code.chmod(0o644)
    edit(mirror)
    result = run(project)
    assert result["edits"] == 1
    assert code.read_text() == 'void Window::f() { tr("New"); }\n'
    assert code.stat().st_mode & 0o777 == 0o644
    for path in (en, de, mirror):
        assert etree.parse(str(path)).findtext(".//source") == "New"
    msg = etree.parse(str(de)).find(".//message")
    assert msg.findtext("translation") == "Alt", "Foreign wording must survive"
    assert msg.findtext("oldsource") == "Old"
    assert msg.find("translation").get("type") == "unfinished"
    assert run(project)["edits"] == 0


def test_apply_when_preview_then_returns_diff_without_writes(project):
    edit(project[-1])
    before = {p: p.read_bytes() for p in project[0].rglob("*") if p.is_file()}
    result = run(project, dry_run=True)
    assert '-void Window::f() { tr("Old"); }' in result["diff"]
    assert all(p.read_bytes() == data for p, data in before.items())


def test_cli_preview_when_edit_ready_then_prints_multiline_diff(project, capsys):
    from vexy_localizzy.cli.sourcefix import apply as cli_apply

    edit(project[-1])
    root, code, en, _, mirror = project
    result = cli_apply(str(mirror), str(en), str(root), dry_run=True)
    assert "diff" not in result
    assert '\n-void Window::f() { tr("Old"); }\n' in capsys.readouterr().out
    assert '"Old"' in code.read_text()


@pytest.mark.parametrize(
    "target,finished", [("Draft", False), ("", True), ("Old", True)]
)
def test_apply_when_no_approved_difference_then_noop(project, target, finished):
    edit(project[-1], new=target, finished=finished)
    result = run(project)
    assert result["edits"] == 0
    assert result["unfinished_edits"] == int(target == "Draft")
    assert '"Old"' in project[1].read_text()


def test_apply_when_source_drifted_then_no_partial_writes(project):
    edit(project[-1])
    project[1].write_text('// unrelated change\nvoid Window::f() { tr("Old"); }\n')
    before = project[2].read_bytes()
    with pytest.raises(ValueError, match="changed since preparation"):
        run(project)
    assert project[2].read_bytes() == before


def test_apply_when_catalog_drifted_then_conflict(project):
    edit(project[-1])
    project[2].write_bytes(project[2].read_bytes() + b"\n")
    with pytest.raises(ValueError, match="changed since preparation"):
        run(project)


def test_apply_when_destination_key_exists_then_conflict(project):
    edit(project[-1])
    catalog(
        project[3],
        [("Old", "../window.cpp", 1, "Alt"), ("New", "../window.cpp", 2, "Neu")],
        "de_DE",
    )
    with pytest.raises(ValueError, match="collision"):
        run(project)
    assert '"Old"' in project[1].read_text()


def test_apply_when_placeholders_change_then_conflict(project):
    edit(project[-1], new="New %1")
    with pytest.raises(ValueError, match="placeholder"):
        run(project)


def test_apply_when_catalog_malformed_then_no_partial_writes(project):
    edit(project[-1])
    project[3].write_text("<broken>")
    with pytest.raises((ValueError, etree.XMLSyntaxError)):
        run(project)
    assert '"Old"' in project[1].read_text()


def test_apply_when_finished_and_draft_coexist_then_preserve_draft(
    tmp_path, monkeypatch
):
    from vexy_localizzy.sourcefix.catalog import Catalog

    monkeypatch.setattr("vexy_localizzy.sourcefix.refresh.rebuild", lambda *args: None)

    code = tmp_path / "a.cpp"
    code.write_text('void Window::f() { tr("Old");\n tr("Draft source"); }\n')
    en, mirror = tmp_path / "en.ts", tmp_path / "edit.ts"
    catalog(en, [("Old", "a.cpp", 1, ""), ("Draft source", "a.cpp", 2, "")])
    prepare(str(en), str(mirror), str(tmp_path))
    monkeypatch.setattr(
        "vexy_localizzy.sourcefix.source.current_locations",
        lambda paths, root, tool: Catalog(en).locations(),
    )
    edit(mirror)
    edit(mirror, old="Draft source", new="Unfinished draft", finished=False)
    apply(str(mirror), str(en), str(tmp_path))
    draft = next(
        m
        for m in etree.parse(str(mirror)).findall(".//message")
        if m.findtext("source") == "Draft source"
    )
    assert draft.findtext("translation") == "Unfinished draft"
    assert draft.find("translation").get("type") == "unfinished"


def test_apply_when_source_identity_edited_then_conflict(project):
    tree = etree.parse(str(project[-1]))
    tree.find(".//source").text = "Changed lookup key"
    tree.write(str(project[-1]))
    with pytest.raises(ValueError, match="identities differ"):
        run(project)


def test_apply_when_matching_is_ambiguous_then_no_write(tmp_path, monkeypatch):
    from vexy_localizzy.sourcefix.catalog import Catalog

    code = tmp_path / "a.cpp"
    code.write_text('void Window::f() { tr("Old"); tr("Old"); }')
    en, mirror = tmp_path / "en.ts", tmp_path / "edit.ts"
    catalog(en, [("Old", "a.cpp", 1, "")])
    prepare(str(en), str(mirror), str(tmp_path))
    monkeypatch.setattr(
        "vexy_localizzy.sourcefix.source.current_locations",
        lambda paths, root, tool: Catalog(en).locations(),
    )
    edit(mirror)
    with pytest.raises(ValueError, match="found 2"):
        apply(str(mirror), str(en), str(tmp_path))
    assert '"New"' not in code.read_text()


def test_apply_when_source_outside_root_then_reject(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "outside.cpp").write_text('tr("Old");')
    en = root / "en.ts"
    catalog(en, [("Old", "../outside.cpp", 1, "")])
    mirror = root / "edit.ts"
    result = prepare(str(en), str(mirror), str(root))
    assert result["external_files_not_editable"] == 1
    edit(mirror)
    with pytest.raises(ValueError, match="outside"):
        apply(str(mirror), str(en), str(root))


def test_apply_when_plural_untouched_then_not_a_correction(project):
    root, _, en, _, mirror = project
    mirror.unlink()
    Path(str(mirror) + ".json").unlink()
    tree = etree.parse(str(en))
    msg = tree.find(".//message")
    msg.set("numerus", "yes")
    msg.find("source").text = "%n font(s)"
    for text in ("%n font", "%n fonts"):
        etree.SubElement(msg.find("translation"), "numerusform").text = text
    tree.write(str(en), encoding="utf-8")
    prepare(str(en), str(mirror), str(root))
    assert run(project)["edits"] == 0
    tree = etree.parse(str(mirror))
    tree.find(".//numerusform").text = "%n typeface"
    tree.write(str(mirror), encoding="utf-8")
    with pytest.raises(ValueError, match="plural"):
        run(project)
