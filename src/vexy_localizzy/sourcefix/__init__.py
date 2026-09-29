# this_file: src/vexy_localizzy/sourcefix/__init__.py
"""Edit English in Qt Linguist, then apply approved wording at its source."""

from vexy_localizzy.sourcefix.apply import apply
from vexy_localizzy.sourcefix.prepare import prepare

__all__ = ["apply", "prepare"]
