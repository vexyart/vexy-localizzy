# this_file: src/vexy_localizzy/translation_cache.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.translate.cache``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.translation_cache"
_NEW = "vexy_localizzy.translate.cache"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
