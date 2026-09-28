# this_file: src/vexy_localizzy/abersetz_transport.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.translate.abersetz_transport``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.abersetz_transport"
_NEW = "vexy_localizzy.translate.abersetz_transport"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
