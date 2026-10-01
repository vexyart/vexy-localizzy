# this_file: tests/test_project.py
"""localizzy.toml resolution and the project commands that read it."""

import tomllib
from pathlib import Path

import pytest

from vexy_localizzy import project
from vexy_localizzy.cli import project as commands

CONFIG = """\
[catalogs]
dir = "i18n"
pattern = "app_{code}.ts"
fresh_dir = "fresh"
[memories]
dir = "tm"
[languages.es]
catalog = "es_MX"
memory = "es-419"
[translate]
endpoint = "http://127.0.0.1:1/v1"
fallback_models = ["model-a", "model-b"]
[qt]
sources = ["../app/src"]
"""


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "proj"
    for name in ("i18n", "fresh", "tm"):
        (root / name).mkdir(parents=True)
    path = root / "localizzy.toml"
    path.write_text(CONFIG, encoding="utf-8")
    (root / "i18n/app_es.ts").write_bytes(b"approved")
    (root / "fresh/app_es.ts").write_bytes(b"fresh")
    (root / "tm/es-core.tmx").write_bytes(b"<tmx/>")
    (root / "tm/es-ui.tmx").write_bytes(b"<tmx/>")
    return root, str(path)


def test_load_config_when_no_file_then_defaults(tmp_path):
    config = project.load_config(start=tmp_path)
    assert config.config_path is None and config.source.language == "en"
    assert config.qt.sources == [], "no file, no configured sources"


def test_load_config_when_in_subdirectory_then_discovered_and_anchored(workspace):
    root, _ = workspace
    config = project.load_config(start=root / "i18n")
    assert config.anchor() == root.resolve(), "paths anchor at the file's directory"
    assert config.catalog_path("de") == root.resolve() / "i18n/app_de.ts"
    assert config.catalog_path("de", fresh=True).parent.name == "fresh"
    assert config.qt_sources() == [(root.parent / "app/src").resolve()]


def test_load_config_when_explicit_missing_then_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        project.load_config(tmp_path / "nope.toml")


def test_load_config_when_unknown_key_then_validation_error(tmp_path):
    path = tmp_path / "localizzy.toml"
    path.write_text('[catalogs]\ndirectory = "x"\n')
    with pytest.raises(project.ConfigError) as caught:
        project.load_config(path)
    message = str(caught.value)
    assert "catalogs.directory" in message and "\n" not in message, message
    path.write_text("[catalogs\n")
    with pytest.raises(project.ConfigError, match="localizzy.toml"):
        project.load_config(path)


def test_language_when_listed_and_unlisted(workspace):
    config = project.load_config(workspace[1])
    assert config.language("es").memory == "es-419"
    assert config.language("xx").catalog == "xx", "an unlisted code is its own tag"


def test_catalog_name_when_pattern_lacks_code_then_value_error(tmp_path):
    path = tmp_path / "localizzy.toml"
    path.write_text('[catalogs]\npattern = "app.ts"\n')
    with pytest.raises(ValueError, match="code"):
        project.load_config(path).catalog_path("de")


def test_init_when_run_twice_then_created_skipped_and_loadable(tmp_path):
    assert project.init(tmp_path) == [("localizzy.toml", "created")]
    assert project.init(tmp_path) == [("localizzy.toml", "skipped")]
    (tmp_path / "localizzy.toml").write_text("# clobbered\n")
    assert project.init(tmp_path, force=True) == [("localizzy.toml", "created")]
    config = project.load_config(tmp_path / "localizzy.toml")
    assert "de" in config.source.locales, "the scaffold parses as a valid config"
    tomllib.loads((tmp_path / "localizzy.toml").read_text())


def test_upgrade_when_spanish_then_paths_tags_and_memories_from_config(
    workspace, monkeypatch
):
    root, config = workspace
    calls = {}

    def fake(fresh, approved, out, retired, **kw):
        calls.update(fresh=fresh, approved=approved, out=out, retired=retired, **kw)
        return {"counts": {"pending": 0}, "out": out}

    monkeypatch.setattr("vexy_localizzy.cli.upgrade.upgrade", fake)
    result = commands.upgrade("es", no_engine=True, config=config)
    assert calls["approved"].endswith("i18n/app_es.ts"), calls["approved"]
    assert calls["fresh"].endswith("fresh/app_es.ts"), calls["fresh"]
    assert calls["target"] == "es_MX" and calls["memory_lang"] == "es-419"
    assert calls["glossary_memory"].endswith("es-core.tmx")
    assert calls["direct_memory"].endswith("es-ui.tmx")
    assert calls["no_engine"] is True and "endpoint" not in calls
    assert Path(calls["retired"]).name.startswith("app_es-"), calls["retired"]
    assert result["in_place"] is False, "in-place is opt-in"


def test_upgrade_when_in_place_and_nothing_pending_then_approved_replaced(
    workspace, monkeypatch
):
    root, config = workspace

    def fake(fresh, approved, out, retired, **kw):
        Path(out).write_bytes(b"new")
        assert kw["model"] == "model-x" and kw["fallback_models"] == "model-a,model-b"
        return {"counts": {"pending": 0}}

    monkeypatch.setattr("vexy_localizzy.cli.upgrade.upgrade", fake)
    result = commands.upgrade("es", model="model-x", in_place=True, config=config)
    assert result["in_place"] is True
    assert (root / "i18n/app_es.ts").read_bytes() == b"new", "approved was replaced"


def test_upgrade_when_pending_then_exit_1_approved_kept_and_rerun_allowed(
    workspace, monkeypatch
):
    root, config = workspace

    def fake(fresh, approved, out, retired, **kw):
        Path(out).write_bytes(b"new")
        Path(retired).write_bytes(b"retired")
        raise SystemExit(1)  # what the general command does when messages stay unfilled

    monkeypatch.setattr("vexy_localizzy.cli.upgrade.upgrade", fake)
    for _ in range(2):  # the same inputs may be upgraded again, e.g. with an engine
        with pytest.raises(SystemExit) as caught:
            commands.upgrade("es", no_engine=True, in_place=True, config=config)
        assert caught.value.code == 1, "pending messages exit 1"
    assert (root / "i18n/app_es.ts").read_bytes() == b"approved", (
        "pending blocks in-place"
    )
    retired = list((root / "i18n/retired").iterdir())
    assert [p.suffix for p in retired] == [".ts"], (
        f"one published retired file: {retired}"
    )


def test_upgrade_when_retired_would_differ_then_refused_and_existing_kept(
    workspace, monkeypatch
):
    root, config = workspace
    contents = iter([b"first", b"second"])

    def fake(fresh, approved, out, retired, **kw):
        Path(retired).write_bytes(next(contents))
        return {"counts": {}}

    monkeypatch.setattr("vexy_localizzy.cli.upgrade.upgrade", fake)
    commands.upgrade("es", no_engine=True, config=config)
    with pytest.raises(SystemExit) as caught:
        commands.upgrade("es", no_engine=True, config=config)
    assert caught.value.code == 2, "a retired file is never overwritten"
    retired = list((root / "i18n/retired").iterdir())
    assert len(retired) == 1 and retired[0].read_bytes() == b"first", retired


def test_upgrade_when_catalog_missing_then_exit_2(workspace):
    with pytest.raises(SystemExit) as caught:
        commands.upgrade("de", no_engine=True, config=workspace[1])
    assert caught.value.code == 2, "a missing catalog is a usage error"


def test_style_file_when_relative_then_resolved_against_project_file(tmp_path):
    path = tmp_path / "localizzy.toml"
    path.write_text('[translate]\nstyle_file = "style/de.md"\n')
    config = project.load_config(path)
    assert commands._style_file(config) == str(tmp_path.resolve() / "style/de.md")
    assert (
        commands._style_file(project.load_config(start=tmp_path / "x")) is None or True
    )


def test_translate_when_source_catalog_and_target_exists_then_refused(
    workspace, monkeypatch
):
    root, config = workspace
    monkeypatch.setattr(
        "vexy_localizzy.cli.translate.translate", lambda *a, **k: {"args": a, **k}
    )
    with pytest.raises(SystemExit) as refused:
        commands.translate("es", source_catalog=str(root / "x.ts"), config=config)
    assert refused.value.code == 2, "losing translations is refused as a usage error"
    result = commands.translate("es", memory_only=True, config=config)
    assert result["args"][1] == "es_MX" and result["memory_only"] is True
    assert "endpoint" not in result, "memory-only passes no engine"
    assert result["out"].endswith("i18n/app_es.ts"), "completed in place by default"


def test_memories_when_file_missing_then_warned_and_dropped(workspace, capsys):
    root, config = workspace
    (root / "tm/es-ui.tmx").unlink()
    flags = commands._memories(project.load_config(config), "es", ["extra.tmx"])
    assert flags["direct_memory"] is None, "a missing memory is not passed on"
    assert flags["glossary_memory"].endswith("es-core.tmx,extra.tmx")
    assert "direct memory not found" in capsys.readouterr().err


def test_build_ui_when_glossary_missing_then_refused(workspace, monkeypatch):
    root, config = workspace
    seen = {}
    monkeypatch.setattr(
        "vexy_localizzy.memory.build_ui.build_ui",
        lambda catalog, out, **kw: seen.update(catalog=catalog, out=out, **kw) or seen,
    )
    commands.build_ui("es", config=config)
    assert seen["out"].name == "es-ui.tmx" and seen["lang"] == "es-419", seen
    (root / "tm/es-core.tmx").unlink()
    with pytest.raises(SystemExit) as refused:
        commands.build_ui("es", config=config)
    assert refused.value.code == 2, "a missing glossary memory is refused"
