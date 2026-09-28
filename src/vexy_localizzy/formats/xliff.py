# this_file: src/vexy_localizzy/formats/xliff.py
"""XLIFF 1.2 output and retained-document editing for XLIFF 1.2 and 2.x."""

from pathlib import Path

from vexy_localizzy.catalog import Catalog
from vexy_localizzy.formats import xliff2, xliff_read, xliff_write
from vexy_localizzy.formats.xliff_xml import read_tree


def load(path: str | Path) -> Catalog:
    raw = Path(path).read_bytes()
    version = read_tree(raw).getroot().get("version", "")
    return xliff2.project(raw) if version.startswith("2.") else xliff_read.project(raw)


def dump(catalog: Catalog, path: str | Path) -> None:
    if catalog.document is not None and catalog.document.format == "xliff":
        version = read_tree(catalog.document.content).getroot().get("version", "")
        if version.startswith("2."):
            return xliff2.dump(catalog, path)
    return xliff_write.dump(catalog, path)


__all__ = ["load", "dump"]
