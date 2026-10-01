# this_file: src/vexy_localizzy/extract/oss.py
"""Fetch upstream UI translations of open-source apps and convert them to TMX.

Sources are shallow, sparse git clones cached under ``<output>/_src`` (or
``cache``). One folder per app, one ``<lang>.tmx`` per language, language codes
shortened to BCP-47 (``de_DE`` -> ``de``, ``pt_BR`` -> ``pt-BR``, ``sr@latin``
-> ``sr-Latn``). The app registry ships as ``oss_apps.toml``; ``registry``
replaces it. PO and Qt TS selection comes from ``legacy_pairs``: fuzzy and
untranslated entries are dropped, plurals give a singular and a plural unit,
``msgctxt`` / Qt context / Fluent id land in ``x-context`` and the source file
in ``x-origin``. Fluent select expressions are expanded per variant (context
suffixed ``[key]``). For Qt TS files ``<TS language>`` wins over the file name.
Ported from the earlier ``oss2tmx`` script; see NOTICE.
"""

import re
import shutil
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path
from typing import Literal

import polib
from loguru import logger
from pydantic import BaseModel, ConfigDict

from vexy_localizzy.extract.fluent_resources import flatten_pattern as flatten_pattern
from vexy_localizzy.extract.fluent_resources import parse_ftl as parse_ftl
from vexy_localizzy.extract.legacy_lang import (
    EXTRA_DEFAULT_REGION,
    PIVOT,
    SCRIPT_TAGS,
    norm_lang,
)
from vexy_localizzy.extract.legacy_pairs import po_pairs as po_units
from vexy_localizzy.extract.legacy_pairs import ts_pairs as ts_units
from vexy_localizzy.extract.legacy_tmx import write_tmx
from vexy_localizzy.extract.mozilla_resources import parse_mozilla as parse_mozilla

__all__ = [
    "APPS",
    "App",
    "Repo",
    "collect",
    "fetch",
    "flatten_pattern",
    "lang_from_path",
    "load_registry",
    "mozilla_units",
    "oss_lang",
    "parse_ftl",
    "parse_mozilla",
    "parse_mozilla_file",
    "run",
]


class Repo(BaseModel):
    """A git repository and optional sparse-checkout patterns (non-cone)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    url: str
    paths: tuple[str, ...] = ()  # empty = whole tree
    branch: str | None = None  # default branch when omitted


class App(BaseModel):
    """One registry entry; ``glob`` is relative to the repo root, ``{lang}`` marks the language."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    repo: Repo
    glob: str
    kind: Literal["po", "ts", "mozilla"] = "po"
    source_repo: Repo | None = None  # Firefox: en-US lives in a second repo
    ignore: str | None = None  # regex on the repo-relative path; matches are skipped


# legacy row: (src, tgt, context, plural-flag, origin)
Row = tuple[str, str, str | None, str | None, str]
MOZILLA_EXTS = (".ftl", ".properties", ".dtd")


def load_registry(path: str | Path | None = None) -> dict[str, App]:
    """Read ``[apps.<name>]`` tables from a TOML file (default: packaged ``oss_apps.toml``)."""
    if path is None:
        data = files("vexy_localizzy.extract").joinpath("oss_apps.toml").read_bytes()
    else:
        data = Path(path).expanduser().read_bytes()
    apps = tomllib.loads(data.decode("utf-8")).get("apps")
    if not isinstance(apps, dict) or not apps:
        raise ValueError(
            f"Registry has no [apps.<name>] tables: {path or 'oss_apps.toml'}"
        )
    return {name: App(name=name, **spec) for name, spec in apps.items()}


APPS: dict[str, App] = load_registry()


# --------------------------------------------------------------------------- #
# Language codes
# --------------------------------------------------------------------------- #


def oss_lang(tag: str) -> str | None:
    """Shortest BCP-47 code for gettext/Qt/KDE spellings; None for pseudo/junk."""
    tag = tag.strip()
    if tag.lower() in ("ua", "ua_ua", "ua-ua"):
        tag = "uk"  # CoolReader spells Ukrainian with the country code
    if tag.lower() in ("en-us", "en_us", "templates", "testing"):
        return PIVOT if tag.lower() in ("en-us", "en_us") else None
    base, _, variant = tag.partition("@")
    base = base.replace("_", "-")
    parts = base.split("-")
    suffix = ""
    if len(parts) > 1 and not parts[1].isalpha():
        suffix = "-" + "-".join(parts[1:])  # de_1901 style variants
        base = parts[0]
    if (
        len(parts) == 2
        and EXTRA_DEFAULT_REGION.get(parts[0].lower()) == parts[1].upper()
    ):
        base = parts[0]
    lang = norm_lang(base)
    if lang is None:
        return None
    if variant:
        variant = SCRIPT_TAGS.get(variant.lower(), variant.lower())
        lang = (
            f"{lang.split('-')[0]}-{variant}"
            if variant in SCRIPT_TAGS.values()
            else f"{lang}-{variant}"
        )
    return lang + suffix


LANG_TOKEN = r"[a-z]{2,3}(?:[-_][A-Za-z0-9]{2,4})*(?:@[a-z]+)?"


def lang_from_path(rel: str, pattern: str) -> str | None:
    """Extract the ``{lang}`` segment of ``rel`` matched against a glob pattern.

    ``{lang}`` only matches a language-code shape (``de``, ``pt_BR``,
    ``sr@latin``, ``zh-Hans``) and ``*`` is lazy, so ``*_{lang}.ts`` splits
    ``qt_help_pt_BR.ts`` into ``qt_help`` + ``pt_BR``.
    """
    regex = re.escape(pattern).replace(r"\*\*/", "(?:.*/)?").replace(r"\*", "[^/]*?")
    regex = regex.replace(r"\{lang\}", f"(?P<lang>{LANG_TOKEN})")
    m = re.fullmatch(regex, rel)
    return m.group("lang") if m and "{lang}" in pattern else None


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #


def git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def fetch(repo: Repo, cache: Path, refresh: bool) -> Path:
    name = re.sub(r"\.git$", "", repo.url.rstrip("/").rsplit("/", 1)[-1])
    host = repo.url.split("/")[2].split(".")[-2]
    dest = cache / f"{host}-{name}"
    if dest.is_dir() and not refresh:
        logger.info("Using cached {}", dest)
        return dest
    shutil.rmtree(dest, ignore_errors=True)
    logger.info("Cloning {} -> {}", repo.url, dest)
    branch = ("--branch", repo.branch) if repo.branch else ()
    git(
        "clone",
        "--quiet",
        "--depth",
        "1",
        "--filter=blob:none",
        "--no-checkout",
        *branch,
        repo.url,
        str(dest),
    )
    if repo.paths:
        git("sparse-checkout", "set", "--no-cone", *repo.paths, cwd=dest)
    git("checkout", "--quiet", cwd=dest)
    return dest


# --------------------------------------------------------------------------- #
# Parsers
# --------------------------------------------------------------------------- #


def parse_po(path: Path, domain: str) -> Iterator[Row]:
    po = polib.pofile(str(path), encoding="utf-8")
    for src, tgt, ctx, plural in po_units(po, fuzzy=False):
        yield src, tgt, ctx, plural, domain


def parse_ts_root(path: Path) -> ET.Element:
    root = ET.parse(path).getroot()
    if root.tag != "TS":
        raise ValueError("Expected a Qt TS document")
    return root


def ts_rows(root: ET.Element, domain: str) -> list[Row]:
    return [(src, tgt, ctx, plural, domain) for src, tgt, ctx, plural in ts_units(root)]


def parse_mozilla_file(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix == ".ftl":
        pairs = parse_ftl(text)
    else:
        pairs = parse_mozilla(text, path.suffix.lstrip("."))
    return {k: v for k, v in pairs if v}


def mozilla_units(loc_root: Path, src_root: Path) -> Iterator[Row]:
    for path in sorted(loc_root.rglob("*")):
        if path.suffix not in MOZILLA_EXTS or not path.is_file():
            continue
        rel = path.relative_to(loc_root).as_posix()
        src_path = src_root / rel
        if not src_path.is_file():
            continue
        source = parse_mozilla_file(src_path)
        for key, tgt in parse_mozilla_file(path).items():
            # Plural/selector variants absent in en-US pair with the default form.
            src = source.get(key)
            if not src and path.suffix == ".ftl":
                src = source.get(re.sub(r"(\[[^\]]*\])+$", "", key))
            if src:
                yield src, tgt, key, None, rel


def collect(app: App, cache: Path, refresh: bool) -> dict[str, list[Row]]:
    root = fetch(app.repo, cache, refresh)
    by_lang: dict[str, list[Row]] = defaultdict(list)
    if app.kind == "mozilla":
        assert app.source_repo is not None
        src_root = fetch(app.source_repo, cache, refresh)
        for loc_dir in sorted(
            p
            for p in root.iterdir()
            if p.is_dir() and not p.name.startswith((".", "_"))
        ):
            lang = oss_lang(loc_dir.name)
            if lang:
                by_lang[lang].extend(mozilla_units(loc_dir, src_root))
        return by_lang
    for path in sorted(root.glob(app.glob.replace("{lang}", "*"))):
        rel = path.relative_to(root).as_posix()
        if app.ignore and re.search(app.ignore, rel):
            logger.debug("Skipping {} (ignored)", rel)
            continue
        raw = lang_from_path(rel, app.glob)
        lang = oss_lang(raw) if raw else None
        if app.kind == "ts":
            ts_root = parse_ts_root(path)
            # ``<TS language>`` beats the file name (``French.ts``, ``ca_CT.ts``).
            lang = oss_lang(ts_root.get("language", "")) or lang
            rows = ts_rows(ts_root, rel)
        else:
            rows = list(parse_po(path, rel))
        if lang is None:
            logger.debug("Skipping {} (language {!r})", rel, raw)
            continue
        by_lang[lang].extend(rows)
    return by_lang


def run(
    output: str,
    apps: str | tuple[str, ...] | None = None,
    registry: str | None = None,
    cache: str | None = None,
    refresh: bool = False,
    verbose: bool = False,
) -> dict:
    """Download upstream translations of open-source apps and write per-language TMX.

    Args:
        output: Folder receiving <app>/<lang>.tmx.
        apps: Comma-separated subset of app names; default all.
        registry: TOML app registry replacing the packaged ``oss_apps.toml``.
        cache: Where git checkouts live (default: <output>/_src).
        refresh: Re-clone repositories even if cached.
        verbose: Debug logging.
    """
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO")
    registered = load_registry(registry) if registry else APPS
    out = Path(str(output)).expanduser()
    cache_dir = Path(cache).expanduser() if cache else out / "_src"
    cache_dir.mkdir(parents=True, exist_ok=True)
    if apps is None:
        names = list(registered)
    elif isinstance(apps, str):
        names = [a.strip() for a in apps.split(",")]
    else:
        names = [str(a).strip() for a in apps]
    unknown = [n for n in names if n not in registered]
    if unknown:
        raise SystemExit(f"Unknown apps {unknown}; choose from {', '.join(registered)}")
    report = []
    for name in names:
        app = registered[name]
        try:
            by_lang = collect(app, cache_dir, refresh)
        except subprocess.CalledProcessError as exc:
            logger.error(
                "{}: git failed: {}", name, exc.stderr.decode(errors="replace").strip()
            )
            report.append({"app": name, "failed": True})
            continue
        app_out = out / name
        app_out.mkdir(parents=True, exist_ok=True)
        total = 0
        for lang, rows in sorted(by_lang.items()):
            if lang == PIVOT:
                continue  # msgid language; nothing to pair
            target = app_out / f"{lang}.tmx"
            n = write_tmx(target, PIVOT, lang, name, rows)
            total += n
            if n == 0:
                target.unlink()
        langs = len(list(app_out.glob("*.tmx")))
        logger.info("{}: {} languages, {} units", name, langs, total)
        report.append(
            {"app": name, "languages": langs, "units": total, "folder": str(app_out)}
        )
    return {"tool": "oss2tmx", "apps": report}
