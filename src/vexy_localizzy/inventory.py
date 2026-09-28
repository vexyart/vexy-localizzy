# this_file: src/vexy_localizzy/inventory.py
"""Bounded XML catalog inventory with file identity and explicit failures."""

import hashlib
import json
import os
import tempfile
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from loguru import logger
from lxml import etree

from vexy_localizzy.xmlio import records

CHUNK_BYTES = 1024 * 1024
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def _identity(stat: os.stat_result) -> tuple[int, ...]:
    """Detect concurrent replacement or modification during inspection."""
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _count_xml(stream, report: dict) -> None:
    """Parse TMX/TS metadata without retaining completed messages."""
    languages, states = Counter(), Counter()
    try:
        for tag, element, namespace in records(stream):
            if tag == "root":
                report["format"] = etree.QName(element).localname
                report["source_language"] = element.get("sourcelanguage", "")
                report["target_language"] = element.get("language", "")
            elif tag == "header":
                report["source_language"] = element.get("srclang", "")
            elif tag == "tu":
                report["units"] += 1
                for tuv in element.findall(namespace + "tuv"):
                    languages[tuv.get(XML_LANG) or tuv.get("lang") or "<missing>"] += 1
            elif tag == "message":
                report["units"] += 1
                translations = element.findall(namespace + "translation")
                states[
                    translations[0].get("type", "finished")
                    if translations
                    else "missing"
                ] += 1
                report["plurals"] += element.get("numerus") == "yes"
                report["length_variants"] += len(
                    element.findall(".//" + namespace + "lengthvariant")
                )
    finally:
        report["languages"] = dict(sorted(languages.items()))
        report["states"] = dict(sorted(states.items()))


def inspect_file(path: str | Path) -> dict:
    """Return hash, exact XML counts and validity; failures never appear valid."""
    path = Path(path)
    report = dict(
        path=str(path),
        status="invalid",
        units=0,
        plurals=0,
        length_variants=0,
        counts_complete=False,
    )
    try:
        before = path.stat()
        report["bytes"] = before.st_size
        with path.open("rb") as stream:
            digest = hashlib.sha256()
            while chunk := stream.read(CHUNK_BYTES):
                digest.update(chunk)
            report["sha256"] = digest.hexdigest()
            stream.seek(0)
            _count_xml(stream, report)
        if _identity(before) != _identity(path.stat()):
            raise ValueError(
                "Source changed during inspection; retry from a stable snapshot"
            )
        report["status"] = "valid"
        report["counts_complete"] = True
    except (OSError, ValueError, etree.XMLSyntaxError) as error:
        report["error"] = str(error)
    return report


def write_inventory(paths: Iterable[Path], output: Path, *, root: Path) -> dict:
    """Write one private JSONL record per input and atomically publish the manifest."""
    output, root = Path(output).resolve(), Path(root).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = dict(files=0, invalid=0, units=0, partial_units=0, bytes=0)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            for path in paths:
                path = Path(os.path.abspath(path))
                if path.resolve() == output:
                    raise ValueError("Inventory output must not overwrite a source")
                relative = path.relative_to(root)
                if not path.resolve().is_relative_to(root):
                    report = dict(
                        status="invalid",
                        units=0,
                        counts_complete=False,
                        error="Resolved source is outside inventory root",
                    )
                else:
                    report = inspect_file(path)
                report["path"] = relative.as_posix()
                stream.write(
                    json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n"
                )
                stream.flush()
                summary["files"] += 1
                summary["invalid"] += report["status"] != "valid"
                summary["units" if report["counts_complete"] else "partial_units"] += (
                    report["units"]
                )
                summary["bytes"] += report.get("bytes", 0)
                logger.debug("Inspected {}: {}", relative, report["status"])
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return summary
