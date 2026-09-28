# this_file: src/vexy_localizzy/qa_tokens.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.qa.tokens``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.qa_tokens"
_NEW = "vexy_localizzy.qa.tokens"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
