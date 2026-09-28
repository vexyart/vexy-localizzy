# this_file: src/vexy_localizzy/cli_upgrade.py
# move-modules: skip
"""Deprecated alias of ``vexy_localizzy.cli.upgrade``; import that path instead."""

import importlib
import sys
import warnings

_OLD = "vexy_localizzy.cli_upgrade"
_NEW = "vexy_localizzy.cli.upgrade"
warnings.warn(f"{_OLD} moved to {_NEW}", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = importlib.import_module(_NEW)
