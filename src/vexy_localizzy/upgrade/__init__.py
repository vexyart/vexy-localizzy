# this_file: src/vexy_localizzy/upgrade/__init__.py
"""TS upgrade: port APPROVED translations onto FRESH lupdate output."""

from vexy_localizzy.upgrade.fuzzy import loose, similarity
from vexy_localizzy.upgrade.identity import MessageRef, identity, message_refs
from vexy_localizzy.upgrade.report import FileInfo, MessageOutcome, UpgradeReport
from vexy_localizzy.upgrade.retired import build_retired, resolve_locations
from vexy_localizzy.upgrade.ts_upgrade import (
    UpgradeInvariantError,
    UpgradeOptions,
    UpgradeResult,
    UpgradeUsageError,
    upgrade,
    upgrade_ts,
)

__all__ = [
    "FileInfo",
    "MessageOutcome",
    "MessageRef",
    "UpgradeInvariantError",
    "UpgradeOptions",
    "UpgradeReport",
    "UpgradeResult",
    "UpgradeUsageError",
    "build_retired",
    "identity",
    "loose",
    "message_refs",
    "resolve_locations",
    "similarity",
    "upgrade",
    "upgrade_ts",
]
