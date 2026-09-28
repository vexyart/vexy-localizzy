# this_file: src/vexy_localizzy/embeddings.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.experimental.embeddings``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.embeddings"
_NEW = "vexy_localizzy.experimental.embeddings"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
