# this_file: src/vexy_localizzy/classification_evidence.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.experimental.classification_evidence``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.classification_evidence"
_NEW = "vexy_localizzy.experimental.classification_evidence"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
