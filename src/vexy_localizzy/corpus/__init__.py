# this_file: src/vexy_localizzy/corpus/__init__.py
"""Voting corpus: sources, snapshots, import, export and lineage.

``Corpus`` is re-exported lazily (PEP 562) because this package used to be the
module ``corpus.py``: ``from vexy_localizzy.corpus.store import Corpus`` keeps working.
Loading it eagerly would cycle, since ``formats.tmx_write`` imports
``corpus.exporter``.
"""

import importlib

__all__ = ["Corpus"]


def __getattr__(name: str):
    if name == "Corpus":
        return importlib.import_module("vexy_localizzy.corpus.store").Corpus
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
