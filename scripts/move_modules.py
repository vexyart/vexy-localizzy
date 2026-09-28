#!/usr/bin/env -S uv run -s
# this_file: scripts/move_modules.py
# move-modules: skip
"""Move top-level ``vexy_localizzy`` modules into subpackages and rewrite imports.

One group per run (``--group qa``) or several (``--group qa,translate``). For each
move the script ``git mv``s the file, creates missing package ``__init__.py``
files, rewrites dotted paths (``vexy_localizzy.qa_tokens`` →
``vexy_localizzy.qa.tokens``), ``from vexy_localizzy import name`` statements and
``vexy_localizzy/old.py`` path strings across the rewrite roots, writes deprecated
alias stubs at the old paths listed in ``STUBS``, then runs ruff on the touched
Python files. Running it again changes nothing. ``--dry-run`` prints the plan.

``--consumer DIR`` rewrites another repository (``src``, ``tests``, ``tools``)
without moving files, for example fl10n. Files carrying the marker
``move-modules: skip`` are never rewritten.

Usage:
    scripts/move_modules.py --group qa [--dry-run]
    scripts/move_modules.py --group all --consumer ../fl10n --dry-run
"""

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

PKG = "vexy_localizzy"
MARKER = "move-modules: skip"
ROOTS = ("src", "tests", "examples", "docs")
EXTRA_FILES = ("NOTICE", "review/vite.config.ts")
CONSUMER_ROOTS = ("src", "tests", "tools")
TEXT_SUFFIXES = {".py", ".md", ".toml", ".ts", ".txt", ".json", ".sh", ""}


def _group(package: str, names: dict[str, str]) -> dict[str, str]:
    return {f"{PKG}.{old}": f"{PKG}.{package}.{new}" for old, new in names.items()}


def _same(package: str, *names: str) -> dict[str, str]:
    return _group(package, {name: name for name in names})


_CLASSIFICATION = [
    "classification",
    "classification_cache",
    "classification_checkpoints",
    "classification_evidence",
    "classification_export",
    "classification_inputs",
    "classification_models",
    "classification_results",
    "classification_run",
    "classification_run_completion",
    "classification_run_inputs",
    "classification_run_store",
    "classification_schedule",
    "classification_store",
]
_DISTILLATION = [
    "distillation",
    "distillation_cache",
    "distillation_chunks",
    "distillation_run",
    "distillation_store",
    "distillation_validation",
]

GROUPS: dict[str, dict[str, str]] = {
    "qa": _group(
        "qa",
        {
            "qa": "text",
            "qa_catalog": "catalog",
            "qa_icu": "icu",
            "qa_markup": "markup",
            "qa_placeholders": "placeholders",
            "qa_printf": "printf",
            "qa_tokens": "tokens",
        },
    ),
    "translate": _group(
        "translate",
        {
            "abersetz_transport": "abersetz_transport",
            "openai_transport": "openai_transport",
            "provider_errors": "provider_errors",
            "translation_types": "types",
            "translation_cache": "cache",
            "translation_store": "store",
            "catalog_translation": "catalog",
            "catalog_translation_inputs": "inputs",
            "catalog_translation_batches": "batches",
            "catalog_translation_types": "catalog_types",
            "frozen_contexts": "frozen_contexts",
        },
    ),
    "memory": _group(
        "memory",
        {"tmx": "tmx_read", "tmx_writer": "tmx_write", "tmx_names": "names"},
    ),
    "cli": {
        f"{PKG}.cli": f"{PKG}.cli",
        **_group(
            "cli",
            {
                "cli_args": "_args",
                "cli_translate": "translate",
                "cli_upgrade": "upgrade",
                "cli_tm": "tm",
            },
        ),
    },
    "extract": {
        **_group("extract", {"source_extraction": "single"}),
        **_same(
            "extract",
            "source_resources",
            "legacy_pairs",
            "apple_resources",
            "fluent_resources",
            "json_resources",
            "mozilla_resources",
            "properties_resources",
        ),
    },
    "review": _group(
        "review",
        {
            "review_api": "api",
            "review_api_data": "api_data",
            "review_journal": "journal",
            "review_server": "server",
            "review_store": "store",
            "review_types": "types",
        },
    ),
    "corpus": {
        **_group(
            "corpus",
            {
                "corpus": "store",
                "corpus_identity": "identity",
                "corpus_schema": "schema",
            },
        ),
        **_same(
            "corpus",
            "importer",
            "exporter",
            "export_lineage",
            "export_selection",
            "lineage_validation",
            "migrations",
            "snapshots",
            "source_store",
            "source_policy",
            "unit_writer",
        ),
    },
    "experimental": _same(
        "experimental",
        *_CLASSIFICATION,
        *_DISTILLATION,
        "embeddings",
        "embedding_search",
        "embedding_store",
        "clustering",
        "retrieval",
    ),
}

# Every old dotted path mapped to its new one, across all groups.
MOVES: dict[str, str] = {
    old: new for group in GROUPS.values() for old, new in group.items()
}

# Non-module directories that move with a group (paths relative to the package).
DIR_MOVES: dict[str, dict[str, str]] = {"review": {"review_web": "review/web"}}

# Old paths that keep a deprecated alias module: every path fl10n imports, plus
# every research module (a live classification run imports the old names).
STUBS: set[str] = {
    f"{PKG}.{name}"
    for name in (
        "qa_catalog",
        "qa_tokens",
        "abersetz_transport",
        "provider_errors",
        "translation_types",
        "translation_cache",
        "catalog_translation",
        "catalog_translation_inputs",
        "catalog_translation_types",
        "cli_translate",
        "cli_upgrade",
        "review_journal",
        "review_server",
        "review_store",
    )
} | set(GROUPS["experimental"])

PACKAGE_DOCS = {
    "qa": "Deterministic content checks: text policy, tokens, placeholders, markup, ICU, catalogs.",
    "cli": "",
    "review": "Optional review server, API and journal (needs the ``review`` extra).",
    "corpus": "Voting corpus: sources, snapshots, import, export and lineage.",
    "experimental": "Research code (classification, distillation, embeddings, clustering, retrieval).\n\nNot part of the supported CLI; APIs may change without notice.",
}

CHAIN = re.compile(
    rf"(?<![\w.])(?P<chain>{PKG}(?:\.\w+)+)(?P<tail>\s+import\s+(?P<name>\w+))?"
)
FROM_PKG = re.compile(rf"^(\s*)from {PKG} import ([^#\n]*?)(\s*#.*)?$", re.M)


def module_file(dotted: str, *, package: bool = False) -> str:
    """Return the ``vexy_localizzy/…`` relative file for a dotted module path."""
    rel = dotted.replace(".", "/")
    return f"{rel}/__init__.py" if package else f"{rel}.py"


def target_file(old: str, new: str) -> str:
    """File that holds ``new``; a module moved onto its own name becomes a package."""
    return module_file(new, package=old == new)


def rewrite_chain(chain: str, moves: dict[str, str]) -> str:
    """Rewrite one dotted chain by its longest moved prefix, unless it is already new."""
    news = {new for old, new in moves.items() if old != new}
    if any(chain == new or chain.startswith(new + ".") for new in news):
        return chain
    parts = chain.split(".")
    for end in range(len(parts), 1, -1):
        prefix = ".".join(parts[:end])
        new = moves.get(prefix)
        if new is not None and new != prefix:
            return ".".join([new, *parts[end:]])
    return chain


def rewrite_from_pkg(match: re.Match, moves: dict[str, str]) -> str:
    """Split ``from vexy_localizzy import a, b as c`` so moved names import from their new home."""
    indent, names, comment = match.group(1), match.group(2), match.group(3) or ""
    if names.strip().startswith("("):
        raise ValueError(f"parenthesized import not supported: {match.group(0)!r}")
    kept: list[str] = []
    lines: list[str] = []
    for item in (part.strip() for part in names.split(",")):
        if not item:
            continue
        name, _, alias = (p.strip() for p in item.partition(" as "))
        new = moves.get(f"{PKG}.{name}")
        if new is None or new == f"{PKG}.{name}":
            kept.append(item)
            continue
        parent, leaf = new.rsplit(".", 1)
        bound = alias or name
        suffix = "" if leaf == bound else f" as {bound}"
        lines.append(f"{indent}from {parent} import {leaf}{suffix}")
    if not lines:
        return match.group(0)
    if kept:
        lines.insert(0, f"{indent}from {PKG} import {', '.join(kept)}")
    lines[-1] += comment
    return "\n".join(lines)


def rewrite_chain_match(match: re.Match, moves: dict[str, str]) -> str:
    """Rewrite a chain, except ``from <new package> import <new module>``.

    ``from vexy_localizzy.corpus import exporter`` names the new package even
    though ``vexy_localizzy.corpus`` is also the old ``corpus.py`` module.
    """
    chain, tail, name = (
        match.group("chain"),
        match.group("tail") or "",
        match.group("name"),
    )
    news = {new for old, new in moves.items() if old != new}
    if name and f"{chain}.{name}" in news:
        return match.group(0)
    return rewrite_chain(chain, moves) + tail


def rewrite_text(text: str, moves: dict[str, str], dirs: dict[str, str]) -> str:
    """Apply every rewrite rule to one file's text; idempotent by construction.

    Chains go first: the ``from vexy_localizzy import name`` rule emits new
    package paths that the chain rule must not see as old module paths.
    """
    text = CHAIN.sub(lambda m: rewrite_chain_match(m, moves), text)
    text = FROM_PKG.sub(lambda m: rewrite_from_pkg(m, moves), text)
    for old, new in moves.items():
        before, after = module_file(old), target_file(old, new)
        if before != after:
            text = re.sub(rf"(?<![\w]){re.escape(before)}(?!\w)", after, text)
    for old, new in dirs.items():
        text = re.sub(rf"(?<![\w]){PKG}/{re.escape(old)}(?![\w])", f"{PKG}/{new}", text)
    return text


def stub_text(old: str, new: str) -> str:
    """Deprecated alias module: the old name becomes the very same module object."""
    return f'''# this_file: src/{module_file(old)}
# {MARKER}
"""Deprecated alias of ``{new}``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "{old}"
_NEW = "{new}"
warnings.warn(f"{{_OLD}} moved to {{_NEW}}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
'''


def is_skipped(path: Path) -> bool:
    try:
        head = path.read_text(encoding="utf-8")[:400]
    except (UnicodeDecodeError, OSError):
        return True
    return MARKER in head


def text_files(
    base: Path, roots: tuple[str, ...], extra: tuple[str, ...]
) -> list[Path]:
    files = [base / name for name in extra if (base / name).is_file()]
    for root in roots:
        top = base / root
        if not top.is_dir():
            continue
        for path in sorted(top.rglob("*")):
            if (
                path.is_file()
                and path.suffix in TEXT_SUFFIXES
                and "__pycache__" not in path.parts
                and "node_modules" not in path.parts
                and not path.name.startswith(".")
            ):
                files.append(path)
    return files


def git(base: Path, *args: str, dry_run: bool) -> None:
    print("git", *args)
    if not dry_run:
        subprocess.run(["git", *args], cwd=base, check=True)


def move_files(base: Path, groups: list[str], dry_run: bool) -> list[Path]:
    """``git mv`` each module still at its old path; return files created or moved."""
    src = base / "src"
    touched: list[Path] = []
    for group in groups:
        for old, new in GROUPS[group].items():
            old_path, new_path = src / module_file(old), src / target_file(old, new)
            if new_path.exists():
                if old_path.exists() and not is_skipped(old_path) and old != new:
                    raise SystemExit(f"both exist: {old_path} and {new_path}")
                continue
            if not old_path.exists():
                raise SystemExit(f"missing: {old_path}")
            if new_path.name == "__init__.py":
                print(f"mkdir {new_path.parent.relative_to(base)}")
                if not dry_run:
                    new_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                ensure_package(src, new_path.parent, dry_run, touched)
            git(
                base,
                "mv",
                str(old_path.relative_to(base)),
                str(new_path.relative_to(base)),
                dry_run=dry_run,
            )
            touched.append(new_path)
        for old, new in DIR_MOVES.get(group, {}).items():
            old_dir, new_dir = src / PKG / old, src / PKG / new
            if new_dir.exists() or not old_dir.exists():
                continue
            ensure_package(src, new_dir.parent, dry_run, touched)
            git(
                base,
                "mv",
                str(old_dir.relative_to(base)),
                str(new_dir.relative_to(base)),
                dry_run=dry_run,
            )
    return touched


def ensure_package(
    src: Path, directory: Path, dry_run: bool, touched: list[Path]
) -> None:
    init = directory / "__init__.py"
    if init.exists() or init in touched:
        return
    name = directory.relative_to(src / PKG).as_posix()
    doc = PACKAGE_DOCS.get(name, "")
    body = f"# this_file: {init.relative_to(src.parent).as_posix()}\n"
    if doc:
        body += f'"""{doc}"""\n'
    print(f"create {init.relative_to(src.parent)}")
    touched.append(init)
    if not dry_run:
        directory.mkdir(parents=True, exist_ok=True)
        init.write_text(body, encoding="utf-8")


def write_stubs(base: Path, groups: list[str], dry_run: bool) -> list[Path]:
    written: list[Path] = []
    for group in groups:
        for old, new in GROUPS[group].items():
            if old not in STUBS or old == new:
                continue
            path = base / "src" / module_file(old)
            body = stub_text(old, new)
            if path.exists() and path.read_text(encoding="utf-8") == body:
                continue
            print(f"stub {path.relative_to(base)} -> {new}")
            written.append(path)
            if not dry_run:
                path.write_text(body, encoding="utf-8")
    return written


def rewrite_files(
    files: list[Path],
    base: Path,
    moves: dict[str, str],
    dirs: dict[str, str],
    dry_run: bool,
) -> list[Path]:
    changed: list[Path] = []
    for path in files:
        if is_skipped(path):
            continue
        before = path.read_text(encoding="utf-8")
        after = rewrite_text(before, moves, dirs)
        if after == before:
            continue
        changed.append(path)
        rel = str(path.relative_to(base))
        diff = difflib.unified_diff(
            before.splitlines(), after.splitlines(), rel, rel, n=0, lineterm=""
        )
        print("\n".join(diff))
        if not dry_run:
            path.write_text(after, encoding="utf-8")
    return changed


def run_ruff(base: Path, paths: list[Path]) -> None:
    py = [str(p) for p in paths if p.suffix == ".py" and p.exists()]
    if not py:
        return
    subprocess.run(
        ["uv", "run", "ruff", "check", "--fix", "--select", "I", "--quiet", *py],
        cwd=base,
        check=False,
    )
    subprocess.run(
        ["uv", "run", "ruff", "format", "--quiet", *py], cwd=base, check=True
    )


def selected(value: str) -> list[str]:
    names = list(GROUPS) if value == "all" else [v.strip() for v in value.split(",")]
    unknown = [name for name in names if name not in GROUPS]
    if unknown:
        raise SystemExit(
            f"unknown group(s): {', '.join(unknown)}; choose from {', '.join(GROUPS)}"
        )
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--group", required=True, help=f"all or a comma list of: {', '.join(GROUPS)}"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the plan, change nothing"
    )
    parser.add_argument(
        "--consumer", type=Path, help="rewrite imports in another repository only"
    )
    args = parser.parse_args(argv)
    groups = selected(args.group)
    moves = {old: new for g in groups for old, new in GROUPS[g].items()}
    dirs = {old: new for g in groups for old, new in DIR_MOVES.get(g, {}).items()}
    if args.consumer:
        base = args.consumer.resolve()
        rewrite_files(
            text_files(base, CONSUMER_ROOTS, ()), base, moves, dirs, args.dry_run
        )
        return 0
    base = Path(__file__).resolve().parent.parent
    touched = move_files(base, groups, args.dry_run)
    changed = rewrite_files(
        text_files(base, ROOTS, EXTRA_FILES), base, moves, dirs, args.dry_run
    )
    stubs = write_stubs(base, groups, args.dry_run)
    if not args.dry_run:
        run_ruff(base, [*touched, *changed, *stubs])
    return 0


if __name__ == "__main__":
    sys.exit(main())
