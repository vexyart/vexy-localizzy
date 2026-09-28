# this_file: src/vexy_localizzy/formats/ts.py
"""Read Qt TS catalogs and apply translation edits to retained XML documents."""

from vexy_localizzy.formats.ts_read import load
from vexy_localizzy.formats.ts_write import dump

__all__ = ["load", "dump"]
