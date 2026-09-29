# this_file: src/vexy_localizzy/cli/sourcefix.py
"""Keep preview diffs multiline instead of Fire's flattened dictionary values."""

from vexy_localizzy.sourcefix import apply as apply_edits
from vexy_localizzy.sourcefix import prepare as prepare_edits
from vexy_localizzy.sourcefix.progress import Progress, report


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
    with Progress():
        mode = "PREVIEW" if dry_run else "APPLY"
        report(f"{mode}: read finished corrections from {mirror}")
        report(f"Root: {root}; English catalog: {source}")
        report(
            "Resolve source edits and rebuild all catalogs and the editing mirror; unfinished drafts are skipped."
        )
        report(
            "Preview only: no files will change."
            if dry_run
            else "Files will be written only after staging and validation finish."
        )
        result = apply_edits(
            mirror, source, root, dry_run=dry_run, verbose=verbose, lupdate=lupdate
        )
        diff = result.pop("diff")
        if diff:
            print(diff, end="" if diff.endswith("\n") else "\n", flush=True)
        report(f"Done: {result['edits']} finished correction(s).")
        return result


def prepare(source: str, out: str, root: str, verbose: bool = False) -> dict:
    """Create the Linguist mirror and snapshot; refuse to overwrite existing work."""
    with Progress():
        report(f"PREPARE: create {out} and its snapshot from {source}")
        result = prepare_edits(source, out, root, verbose=verbose)
        report("Done: open the mirror in Qt Linguist and mark corrections finished.")
        return result


COMMANDS = {"prepare": prepare, "apply": apply}
