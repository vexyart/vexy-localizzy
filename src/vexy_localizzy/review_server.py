# this_file: src/vexy_localizzy/review_server.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.review.server``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.review_server"
_NEW = "vexy_localizzy.review.server"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
