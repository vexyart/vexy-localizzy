# this_file: tests/qt/test_qt_applang.py
"""applang over a synthetic app bundle with UTF-16 Qt resource names."""

import os
import plistlib
import shlex
import stat
import subprocess
from pathlib import Path

import pytest

from vexy_localizzy.qt import applang

PAD = (
    b"XX"  # non-null padding so one byte order cannot match the other shifted by a byte
)


def _bundle(tmp_path: Path, *, plist: bool = True) -> Path:
    """'Demo App.app' whose executable embeds de (big-endian) and pt_BR (little-endian)."""
    bundle = tmp_path / "Demo App.app"
    macos = bundle / "Contents" / "MacOS"
    macos.mkdir(parents=True)
    data = (
        PAD
        + "demo_de.qm".encode("utf-16-be")
        + PAD
        + "demo_pt_BR.qm".encode("utf-16-le")
        + PAD
        + "other_fr.qm".encode("utf-16-le")
        + PAD
    )
    (macos / "Demo App").write_bytes(data)
    (macos / "libextra.dylib").write_bytes(b"\x00" * 1000)
    if plist:
        info = {"CFBundleExecutable": "Demo App"}
        (bundle / "Contents" / "Info.plist").write_bytes(plistlib.dumps(info))
    return bundle


@pytest.mark.parametrize("plist", [True, False])
def test_languages_when_both_byte_orders_then_all_codes_found(tmp_path, plist):
    codes = applang.languages(_bundle(tmp_path, plist=plist), "demo")
    assert codes == ["de", "en", "pt_BR"], (
        f"expected BE de, LE pt_BR and source en, got {codes}"
    )


def test_languages_when_custom_source_language_then_included(tmp_path):
    codes = applang.languages(_bundle(tmp_path), "demo", source_language="fr")
    assert codes == ["de", "fr", "pt_BR"], f"source language must be listed: {codes}"


@pytest.mark.parametrize(
    ("make", "prefix", "message"),
    [
        (lambda p: p / "Missing.app", "demo", "not an app bundle"),
        (lambda p: _bundle(p), "", "prefix"),
        (
            lambda p: (p / "Empty.app").mkdir() or p / "Empty.app",
            "demo",
            "no executable",
        ),
    ],
)
def test_languages_when_bad_input_then_value_error(tmp_path, make, prefix, message):
    with pytest.raises(ValueError, match=message):
        applang.languages(make(tmp_path), prefix)


def test_run_when_not_macos_then_runtime_error(tmp_path, monkeypatch):
    monkeypatch.setattr(applang.platform, "system", lambda: "Linux")
    with pytest.raises(RuntimeError, match="macOS"):
        applang.run(_bundle(tmp_path), "de", "demo")


@pytest.fixture
def mac_open(monkeypatch):
    calls = []
    monkeypatch.setattr(applang.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        applang.subprocess,
        "run",
        lambda cmd, **kw: (
            calls.append((cmd, kw)) or subprocess.CompletedProcess(cmd, 0)
        ),
    )
    return calls


def test_run_when_region_code_in_other_case_then_matched(tmp_path, mac_open):
    bundle = _bundle(tmp_path)
    command = applang.run(bundle, "pt-br", "demo")
    assert command == [
        "open",
        "-a",
        str(bundle),
        "--args",
        "-AppleLanguages",
        "(pt_BR)",
    ], f"command: {command}"
    assert mac_open[0][1]["timeout"] == applang.OPEN_TIMEOUT, (
        "open must run with a timeout"
    )


def test_run_when_new_then_private_tmpdir(tmp_path, mac_open):
    command = applang.run(_bundle(tmp_path), "de", "demo", new=True)
    assert command[:3] == ["open", "-n", "--env"], f"new instance flags: {command}"
    tmpdir = Path(command[3].removeprefix("TMPDIR="))
    assert tmpdir.is_dir(), f"private TMPDIR must exist: {tmpdir}"
    tmpdir.rmdir()


def test_run_when_language_not_shipped_then_value_error(tmp_path, mac_open):
    with pytest.raises(ValueError, match="no 'ja' UI"):
        applang.run(_bundle(tmp_path), "ja", "demo")
    assert mac_open == [], "nothing may launch for an unknown language"


def test_write_commands_when_bundle_then_one_launcher_per_language(tmp_path):
    bundle = _bundle(tmp_path)
    out = tmp_path / "launchers"
    written = applang.write_commands(bundle, "demo", out)
    assert [p.name for p in written] == [
        "demo-app-de.command",
        "demo-app-en.command",
        "demo-app-pt_BR.command",
    ], f"names: {written}"
    script = (out / "demo-app-pt_BR.command").read_text(encoding="utf-8")
    assert script.startswith("#!/bin/bash\n"), "launcher must be a bash script"
    assert f"-a {shlex.quote(str(bundle.resolve()))} " in script, (
        f"bundle path must be shell-quoted: {script}"
    )
    assert '-AppleLanguages "(pt_BR)"' in script and "open -n --env" in script, (
        f"launch line: {script}"
    )
    assert "this_file" not in script, "generated launchers carry no source-tree header"
    assert os.stat(written[0]).st_mode & stat.S_IXUSR, "launcher must be executable"


def test_write_commands_when_name_given_then_used_as_slug(tmp_path):
    written = applang.write_commands(
        _bundle(tmp_path), "demo", tmp_path, name="My Tool"
    )
    assert written[0].name == "my-tool-de.command", f"name slug: {written[0].name}"


def test_write_commands_when_bundle_name_has_newline_then_no_injected_line(tmp_path):
    bundle = tmp_path / "Evil\ntouch pwned\n.app"
    macos = bundle / "Contents" / "MacOS"
    macos.mkdir(parents=True)
    (macos / "Evil").write_bytes(PAD + "demo_de.qm".encode("utf-16-be") + PAD)
    path = applang.write_commands(bundle, "demo", tmp_path / "out", name="evil")[0]
    script = path.read_text(encoding="utf-8")
    header, comment, _, command = script.split("\n", 3)
    assert "\n" not in comment and "touch pwned" in comment, (
        f"comment stays one line: {comment!r}"
    )
    argv = shlex.split(command)
    assert argv[argv.index("-a") + 1] == str(bundle.resolve()), (
        f"path must stay one quoted word: {argv}"
    )
    assert "touch" not in argv, f"no command may be injected: {argv}"
    result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    assert result.returncode == 0, f"launcher must be valid bash: {result.stderr}"


def test_write_commands_when_launcher_exists_then_replaced_and_executable(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    stale = out / "demo-app-de.command"
    stale.write_text("stale", encoding="utf-8")
    stale.chmod(0o600)
    applang.write_commands(_bundle(tmp_path), "demo", out)
    assert stale.read_text(encoding="utf-8").startswith("#!/bin/bash"), (
        "launcher must be replaced"
    )
    assert stat.S_IMODE(os.stat(stale).st_mode) == applang.LAUNCHER_MODE, (
        "launcher mode must be 0755"
    )
    assert not [p for p in out.iterdir() if p.name.endswith(".tmp")], (
        "no temporary files remain"
    )


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, ["open"]),
        subprocess.TimeoutExpired(["open"], 60),
    ],
)
def test_run_when_open_fails_then_runtime_error(tmp_path, monkeypatch, error):
    monkeypatch.setattr(applang.platform, "system", lambda: "Darwin")

    def fail(cmd, **kwargs):
        raise error

    monkeypatch.setattr(applang.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="could not launch"):
        applang.run(_bundle(tmp_path), "de", "demo")
