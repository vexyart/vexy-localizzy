# this_file: src/vexy_localizzy/doctor.py
"""Environment report: platform, Python, external tools and optional extras.

No network and no installation. Each gap comes with the command that closes
it, for a person to run. Referenced by ``localizzy doctor``.
"""

import platform
import sys
from dataclasses import dataclass, field

from vexy_localizzy.external import (
    EXTRA_IMPORTS,
    QT_BINARIES,
    TT_BINARIES,
    extra_installed,
    find_tool,
    install_command,
    os_install_hint,
)


@dataclass(frozen=True)
class DoctorReport:
    platform: str
    python: str
    tools: dict[str, dict] = field(default_factory=dict)
    extras: dict[str, bool] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)


def run() -> DoctorReport:
    """Probe the tools and extras; list one suggestion per distinct gap."""
    tools: dict[str, dict] = {}
    suggestions: list[str] = []
    for name in (*QT_BINARIES, *TT_BINARIES):
        info = find_tool(name)
        tools[name] = {"found": info.found, "path": info.path, "version": info.version}
        if not info.found:
            hint = (
                os_install_hint()
                if name in QT_BINARIES
                else install_command("pofilter")
            )
            suggestions.append(f"{name}: not found; install with `{hint}`")
    extras = {extra: extra_installed(extra) for extra in EXTRA_IMPORTS}
    suggestions += [
        f"[{extra}] extra: install with `{install_command(extra)}`"
        for extra, installed in extras.items()
        if not installed
    ]
    version = sys.version_info
    return DoctorReport(
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
        python=f"{version.major}.{version.minor}.{version.micro}",
        tools=tools,
        extras=extras,
        suggestions=list(dict.fromkeys(suggestions)),
    )


def render(report: DoctorReport) -> str:
    """The report as plain text."""
    lines = [f"platform: {report.platform}", f"python:   {report.python}"]
    lines.append("external tools:")
    for name, info in report.tools.items():
        status = (info["version"] or info["path"]) if info["found"] else "MISSING"
        lines.append(f"  {name:10s} {status}")
    lines.append("python extras:")
    for extra, installed in report.extras.items():
        lines.append(f"  {extra:12s} {'installed' if installed else 'not installed'}")
    if report.suggestions:
        lines.append("suggestions:")
        lines += [f"  - {suggestion}" for suggestion in report.suggestions]
    return "\n".join(lines)
