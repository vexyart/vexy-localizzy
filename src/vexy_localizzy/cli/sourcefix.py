# this_file: src/vexy_localizzy/cli/sourcefix.py
"""Keep preview diffs multiline instead of Fire's flattened dictionary values."""

from vexy_localizzy.sourcefix import apply as apply_edits
from vexy_localizzy.sourcefix import prepare


def apply(
    mirror: str,
    source: str,
    root: str,
    dry_run: bool = False,
    verbose: bool = False,
    lupdate: str = "lupdate",
) -> dict:
    """Apply finished English edits; --dry-run prints a diff without writing.

    Uses MIRROR.json from source-fix prepare. Qt lupdate verifies current source
    identities. Foreign translations survive unfinished for review; plurals and
    conflicting or stale source edits are rejected before writes.
    """
    result = apply_edits(
        mirror, source, root, dry_run=dry_run, verbose=verbose, lupdate=lupdate
    )
    diff = result.pop("diff")
    if diff:
        print(diff, end="" if diff.endswith("\n") else "\n")
    return result


COMMANDS = {"prepare": prepare, "apply": apply}
