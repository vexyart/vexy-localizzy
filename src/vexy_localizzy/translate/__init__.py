# this_file: src/vexy_localizzy/translate/__init__.py
"""Memory-aware catalog translation: kept targets, direct and glossary memory, engine."""

from vexy_localizzy.translate.context import GlossaryContext
from vexy_localizzy.translate.engine import EngineSpec, open_cache
from vexy_localizzy.translate.run import (
    MemoryPolicy,
    TranslateReport,
    UnitProvenance,
    memory_prefill,
    translate_file,
)

__all__ = [
    "EngineSpec",
    "GlossaryContext",
    "MemoryPolicy",
    "TranslateReport",
    "UnitProvenance",
    "memory_prefill",
    "open_cache",
    "translate_file",
]
