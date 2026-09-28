# this_file: src/vexy_localizzy/qa/__init__.py
"""Deterministic content checks: text policy, tokens, placeholders, markup, ICU, catalogs.

The package re-exports the text-level entry points; catalog, token, ICU and
printf checks live in their submodules.
"""

from vexy_localizzy.qa.text import TextPolicy, check_text, validate_batch

__all__ = ["TextPolicy", "check_text", "validate_batch"]
