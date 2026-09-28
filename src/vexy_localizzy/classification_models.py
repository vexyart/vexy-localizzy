# this_file: src/vexy_localizzy/classification_models.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.experimental.classification_models``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.classification_models"
_NEW = "vexy_localizzy.experimental.classification_models"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
