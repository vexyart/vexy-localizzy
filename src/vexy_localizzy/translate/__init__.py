# this_file: src/vexy_localizzy/translate/__init__.py
"""Memory-aware catalog translation: kept targets, direct and glossary memory, engine.

Exports resolve lazily (PEP 562) so importing a leaf module such as
``vexy_localizzy.translate.types`` does not load the whole orchestration stack;
``qa.text`` imports ``translate.types`` and ``translate.run`` imports ``qa``.
"""

import importlib

_EXPORTS = {
    "GlossaryContext": "vexy_localizzy.translate.context",
    "EngineSpec": "vexy_localizzy.translate.engine",
    "open_cache": "vexy_localizzy.translate.engine",
    "MemoryPolicy": "vexy_localizzy.translate.run",
    "TranslateReport": "vexy_localizzy.translate.run",
    "UnitProvenance": "vexy_localizzy.translate.run",
    "memory_prefill": "vexy_localizzy.translate.run",
    "translate_file": "vexy_localizzy.translate.run",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str):
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module), name)


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
