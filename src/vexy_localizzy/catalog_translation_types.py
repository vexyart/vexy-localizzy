# this_file: src/vexy_localizzy/catalog_translation_types.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.translate.catalog_types``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.catalog_translation_types"
_NEW = "vexy_localizzy.translate.catalog_types"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
