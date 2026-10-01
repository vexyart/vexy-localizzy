# this_file: src/vexy_localizzy/qt/applang.py
"""Launch a macOS Qt app in a chosen UI language and list the languages it ships.

A Qt app on macOS that follows the system language list honours a
``-AppleLanguages "(code)"`` launch argument; it overrides the saved language
preference for that process only. Translations are usually compiled into the
executable as Qt resources named ``<prefix>_<code>.qm``, so ``languages`` scans
the executable for those names instead of trusting a hard-coded table.

Apps built on QtSingleApplication allow one running instance: a second copy
finds the first one's lock socket under ``$TMPDIR`` and quits at once, so
``open -n`` alone is not enough. A new instance therefore gets its own empty
TMPDIR (``open --env``), which is where that lock lives.

Every function takes the app bundle path and the ``.qm`` resource prefix
explicitly; there is no built-in app table.
"""

import platform
import plistlib
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

from vexy_localizzy.formats.document import atomic_write

# Seconds; `open` returns as soon as Launch Services accepts the request.
OPEN_TIMEOUT = 60
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")
LAUNCHER_MODE = 0o755


def _bundle(app: str | Path) -> Path:
    bundle = Path(app).expanduser()
    if not bundle.is_dir():
        raise ValueError(f"not an app bundle: {bundle}")
    return bundle


def _executable(bundle: Path) -> Path:
    """The bundle's ``CFBundleExecutable``, else the largest non-dylib file."""
    macos = bundle / "Contents" / "MacOS"
    info = bundle / "Contents" / "Info.plist"
    if info.is_file():
        name = plistlib.loads(info.read_bytes()).get("CFBundleExecutable")
        if name and (macos / name).is_file():
            return macos / name
    candidates = (
        [p for p in macos.iterdir() if p.is_file() and p.suffix != ".dylib"]
        if macos.is_dir()
        else []
    )
    if not candidates:
        raise ValueError(f"no executable under {macos}")
    return max(candidates, key=lambda p: p.stat().st_size)


def _resource_patterns(prefix: str) -> tuple[re.Pattern[bytes], re.Pattern[bytes]]:
    """Big- and little-endian UTF-16 patterns for ``<prefix>_<code>.qm``.

    Qt's rcc stores resource names as UTF-16, so a plain ``strings`` scan
    misses them; both byte orders occur depending on the build.
    """
    stem = prefix + "_"
    be = re.compile(
        re.escape(stem.encode("utf-16-be"))
        + rb"((?:\x00[a-z]){2,3}(?:\x00_(?:\x00[A-Za-z]){2,4})?)\x00\.\x00q\x00m"
    )
    le = re.compile(
        re.escape(stem.encode("utf-16-le"))
        + rb"((?:[a-z]\x00){2,3}(?:_\x00(?:[A-Za-z]\x00){2,4})?)\.\x00q\x00m\x00"
    )
    return be, le


def languages(app: str | Path, prefix: str, source_language: str = "en") -> list[str]:
    """Sorted language codes with a ``<prefix>_<code>.qm`` in the executable.

    ``source_language`` is always included: the untranslated UI needs no
    ``.qm``. Raises ``ValueError`` for a missing bundle, executable or prefix.
    """
    if not prefix:
        raise ValueError(
            "prefix must name the .qm resources, e.g. 'myapp' for myapp_de.qm"
        )
    data = _executable(_bundle(app)).read_bytes()
    be, le = _resource_patterns(prefix)
    found = {m.group(1).decode("utf-16-be") for m in be.finditer(data)}
    found |= {m.group(1).decode("utf-16-le") for m in le.finditer(data)}
    return sorted(found | {source_language})


def run(
    app: str | Path,
    lang: str,
    prefix: str,
    new: bool = False,
    source_language: str = "en",
) -> list[str]:
    """Launch ``app`` with ``-AppleLanguages "(lang)"`` and return the command used.

    With ``new`` a separate instance starts (``open -n`` with a private
    TMPDIR); without it a running copy is only brought to front and keeps its
    current language. Raises ``RuntimeError`` off macOS or when ``open``
    fails or times out, and ``ValueError`` for a language the app does not ship.
    """
    if platform.system() != "Darwin":
        raise RuntimeError("launching an app bundle requires macOS")
    bundle = _bundle(app)
    available = languages(bundle, prefix, source_language)
    wanted = lang.strip().replace("-", "_").lower()
    code = next((c for c in available if c.lower() == wanted), None)
    if code is None:
        raise ValueError(
            f"{bundle.name} has no {lang!r} UI; available: {', '.join(available)}"
        )
    command = ["open"]
    if new:
        command += [
            "-n",
            "--env",
            f"TMPDIR={tempfile.mkdtemp(prefix=f'applang-{code}-')}",
        ]
    command += ["-a", str(bundle), "--args", "-AppleLanguages", f"({code})"]
    try:
        subprocess.run(command, check=True, timeout=OPEN_TIMEOUT)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"could not launch {bundle.name}: {error}") from error
    return command


def _comment_safe(text: str) -> str:
    """Drop control characters (newlines included) so text cannot leave a comment."""
    return _CONTROL_RE.sub("", text)


def _launcher(bundle: Path, name: str, code: str) -> str:
    return (
        "#!/bin/bash\n"
        f"# Launch a new {_comment_safe(bundle.stem)} instance with the {code} UI (overrides the saved language).\n"
        "# A private TMPDIR keeps it clear of the running copy's single-instance lock.\n"
        f'open -n --env "TMPDIR=$(mktemp -d -t applang-{name}-{code})" '
        f'-a {shlex.quote(str(bundle))} --args -AppleLanguages "({code})"\n'
    )


def write_commands(
    app: str | Path, prefix: str, out: str | Path, name: str | None = None
) -> list[Path]:
    """Write one double-clickable ``<name>-<lang>.command`` per language into ``out``.

    Each launcher starts a new instance with a private TMPDIR. ``name``
    defaults to a slug of the bundle name. Returns the written paths.
    """
    bundle = _bundle(app).resolve()
    slug = _SLUG_RE.sub("-", (name or bundle.stem).lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot derive a launcher name from {name or bundle.stem!r}")
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for code in languages(bundle, prefix):
        path = folder / f"{slug}-{code}.command"
        atomic_write(path, _launcher(bundle, slug, code).encode("utf-8"))
        path.chmod(LAUNCHER_MODE)
        written.append(path)
    return written
