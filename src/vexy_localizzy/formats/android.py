# this_file: src/vexy_localizzy/formats/android.py
"""Android resource adapter with preserved documents and explicit monolingual output."""

from vexy_localizzy.formats.android_read import load
from vexy_localizzy.formats.android_write import dump

__all__ = ["load", "dump"]
