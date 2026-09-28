# this_file: src/vexy_localizzy/formats/json_io.py
"""Versioned canonical JSON; unrelated application JSON is a separate format."""

from pathlib import Path

from vexy_localizzy.catalog import Catalog
from vexy_localizzy.formats.document import atomic_write


def load(path: str | Path) -> Catalog:
    return Catalog.model_validate_json(Path(path).read_bytes())


def dump(catalog: Catalog, path: str | Path) -> None:
    content = catalog.model_dump_json(indent=2).encode("utf-8") + b"\n"
    Catalog.model_validate_json(content)
    atomic_write(path, content)
