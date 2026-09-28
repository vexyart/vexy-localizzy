# this_file: src/vexy_localizzy/provider_errors.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.translate.provider_errors``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.provider_errors"
_NEW = "vexy_localizzy.translate.provider_errors"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
