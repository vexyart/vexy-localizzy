# this_file: src/vexy_localizzy/translate/context.py
"""Prompt context for catalog batches: style plus only the glossary terms in the batch."""

from collections.abc import Callable

from vexy_localizzy.memory.glossary import Glossary
from vexy_localizzy.translate.catalog_types import PromptContext
from vexy_localizzy.translate.types import TranslationExample, TranslationItem


class GlossaryContext:
    """`translate_catalog` context callback.

    Each call receives one batch's items and returns the style guidance, the
    glossary terms occurring in those items (``Glossary.relevant``, deterministic
    order so cache keys stay stable) and optional retrieved examples.
    ``used_terms`` records, per item id, the term ids sent with its batch that
    occur in that item's own source; it feeds the provenance report.
    """

    def __init__(
        self,
        glossary: Glossary | None,
        *,
        style: str = "",
        examples: Callable[[list[TranslationItem]], list[TranslationExample]]
        | None = None,
        limit: int = 60,
    ) -> None:
        self.glossary = glossary
        self.style = style
        self.examples = examples
        self.limit = limit
        self.used_terms: dict[str, set[str]] = {}
        self._ids = (
            {term.source: term.term_id for term in glossary.terms} if glossary else {}
        )

    def __call__(self, items: list[TranslationItem]) -> PromptContext:
        glossary: dict[str, str] = {}
        if self.glossary is not None:
            glossary = self.glossary.relevant(
                [item.source for item in items], limit=self.limit
            )
            for item in items:
                own = self.glossary.relevant([item.source], limit=len(self._ids) or 1)
                self.used_terms[item.id] = {
                    self._ids[source] for source in own if source in glossary
                }
        examples = self.examples(items) if self.examples else []
        return PromptContext(style=self.style, glossary=glossary, examples=examples)
