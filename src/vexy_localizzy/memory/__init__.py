# this_file: src/vexy_localizzy/memory/__init__.py
"""Read-only translation memories: direct UI memory and core glossary."""

from vexy_localizzy.memory.direct import (
    DirectMemory,
    MatchClass,
    MemoryEntry,
    MemoryHit,
    normalize_source,
)
from vexy_localizzy.memory.glossary import Glossary, Term, match_text
from vexy_localizzy.memory.langmatch import select_language

__all__ = [
    "DirectMemory",
    "Glossary",
    "MatchClass",
    "MemoryEntry",
    "MemoryHit",
    "Term",
    "match_text",
    "normalize_source",
    "select_language",
]
