# this_file: src/vexy_localizzy/catalog_translation.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.translate.catalog``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.catalog_translation"
_NEW = "vexy_localizzy.translate.catalog"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
