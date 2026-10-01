# this_file: src/vexy_localizzy/memory/lookup.py
"""Find every exact source match of a Qt catalog in language-prefixed memories.

For each distinct source of a ``.ts`` catalog (and, optionally, of a ``.qph``
phrase book) list every translation that any ``<lang>-*.tmx`` memory in a
folder holds for it, with the memory files that hold it. The result is
evidence for a terminology decision: which rendering other products use, and
how many sources agree. Catalog and phrase-book translations are never read.
Matching is case-sensitive, trims outer whitespace and drops ``&`` accelerator
markers. Referenced by ``localizzy tm lookup``.
"""

import json
import re
import sys
from pathlib import Path

from loguru import logger
from lxml import etree

from vexy_localizzy.formats import ts_xml
from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.tmx_read import read_tmx

TEMPLATE = Path(__file__).with_suffix(".html")
ACCELERATOR = re.compile(r"&&|&(?=[^\s&])(?!#?\w+;)")
LANGUAGE_CODE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)*")

Matches = dict[str, dict[str, dict[str, list[str]]]]


def plain(text: str) -> str:
    """Trim and drop Qt accelerator markers; keep literal ``&&``, lone ``&``, entities."""
    if "&" in text:
        text = ACCELERATOR.sub(lambda m: m.group() if m.group() == "&&" else "", text)
    return text.strip()


def _qph_sources(path: Path) -> list[str]:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    tree = etree.parse(str(path), parser)
    dtd = tree.docinfo.internalDTD
    if dtd is not None and list(dtd.iterentities()):
        raise ValueError("QPH entity declarations are not supported")
    root = tree.getroot()
    if etree.QName(root).localname != "QPH":
        raise ValueError(f"Expected a QPH root: {path}")
    uri = etree.QName(root).namespace
    ns = f"{{{uri}}}" if uri else ""
    return [plain(ts_xml.text(p, ns)) for p in root.findall(f"{ns}phrase/{ns}source")]


def input_sources(ts_path: Path, qph_path: Path | None = None) -> tuple[list[str], str]:
    """Distinct plain sources of every message status, and the source language."""
    tree, ns = ts_xml.parse(ts_path.read_bytes())
    sources = [
        plain(ts_xml.text(message.find(ns + "source"), ns))
        for _, message in ts_xml.messages(tree.getroot(), ns)
        if message.find(ns + "source") is not None
    ]
    if qph_path:
        sources.extend(_qph_sources(qph_path))
    language = canonical_locale(tree.getroot().get("sourcelanguage") or "en")
    return sorted(set(sources), key=lambda s: (s.casefold(), s)), language


def language_matches(tag: str, wanted: str) -> bool:
    """A base language includes its regional variants; an explicit tag stays scoped."""
    return tag == wanted or tag.startswith(wanted + "-")


def lookup(
    sources: list[str], source_language: str, languages: list[str], directory: Path
) -> Matches:
    """Stream each memory once; keep exact plain-text matches and their file names."""
    result: Matches = {source: {lang: {} for lang in languages} for source in sources}
    source_base = source_language.split("-")[0]
    for language in languages:
        files = sorted(directory.glob(f"{language}-*.tmx"))
        if not files:
            logger.warning("No {}-*.tmx files in {}", language, directory)
        for path in files:
            logger.debug("Reading {}", path)
            for unit in read_tmx(path):
                originals = {
                    plain(segment.text)
                    for segment in unit.segments
                    if language_matches(segment.language, source_base)
                } & result.keys()
                targets = [
                    plain(segment.text)
                    for segment in unit.segments
                    if language_matches(segment.language, language)
                ]
                for source in originals:
                    for target in targets:
                        names = result[source][language].setdefault(target, [])
                        if not names or names[-1] != path.name:
                            names.append(path.name)
        matched = sum(bool(row[language]) for row in result.values())
        logger.info("{}: {} / {} sources matched", language, matched, len(result))
    return result


def render_report(data: Matches, languages: list[str]) -> str:
    """One self-contained HTML page with the data embedded as JSON."""
    payload = json.dumps({"languages": languages, "data": data}, ensure_ascii=False)
    template = TEMPLATE.read_text(encoding="utf-8")
    return template.replace("__PAYLOAD__", payload.replace("<", "\\u003c"))


def _languages(langs: object) -> list[str]:
    from vexy_localizzy.cli._args import csv_strings

    codes = csv_strings(langs)
    if not codes or any(not LANGUAGE_CODE.fullmatch(code) for code in codes):
        raise ValueError("Invalid language codes; use for example --langs de,es,fr")
    return list(dict.fromkeys(canonical_locale(code) for code in codes))


def _outputs(ts_path: Path, out: str | None, report: str | None) -> list[Path | None]:
    """Default beside the catalog; an empty string turns an output off."""
    defaults = (ts_path.name + ".lookup.json", ts_path.name + ".lookup.html")
    return [
        None if value == "" else Path(value) if value else ts_path.with_name(default)
        for value, default in zip((out, report), defaults)
    ]


def run(
    ts: str,
    tmx_dir: str,
    langs: str,
    qph: str | None = None,
    out: str | None = None,
    report: str | None = None,
    verbose: bool = False,
) -> dict:
    """Look up every source of TS in the ``<lang>-*.tmx`` memories of TMX_DIR.

    --langs de,es,fr names the memory prefixes. --qph adds a phrase book's
    sources. JSON goes to --out (default TS.lookup.json) and the filterable page
    to --report (default TS.lookup.html); pass an empty string to skip either.
    Sources without any match are left out of both.
    """
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO")
    ts_path, directory = Path(ts).resolve(), Path(tmx_dir).resolve()
    qph_path = Path(qph).resolve() if qph else None
    if not directory.is_dir():
        raise ValueError(f"Missing TMX directory: {directory}")
    languages = _languages(langs)
    json_out, report_out = _outputs(ts_path, out, report)
    chosen = [path.resolve() for path in (json_out, report_out) if path is not None]
    protected = {ts_path, qph_path, *directory.glob("*.tmx")}
    if len(chosen) != len(set(chosen)) or protected.intersection(chosen):
        raise ValueError("Output paths would overwrite an input or each other")
    sources, source_language = input_sources(ts_path, qph_path)
    found = lookup(sources, source_language, languages, directory)
    found = {source: row for source, row in found.items() if any(row.values())}
    if json_out:
        text = json.dumps(found, ensure_ascii=False, indent=2) + "\n"
        atomic_write(json_out, text.encode("utf-8"))
    if report_out:
        atomic_write(report_out, render_report(found, languages).encode("utf-8"))
    return {
        "sources": len(sources),
        "matched": len(found),
        "languages": languages,
        "json": str(json_out) if json_out else None,
        "report": str(report_out) if report_out else None,
    }
