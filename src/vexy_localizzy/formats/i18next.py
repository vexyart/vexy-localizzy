# this_file: src/vexy_localizzy/formats/i18next.py
"""i18next v4 monolingual resources with exact document and scoped edit fidelity."""

import re
from pathlib import Path

from vexy_localizzy.catalog import Catalog, Placeholder, PluralForms, Unit
from vexy_localizzy.formats.document import SourceDocument
from vexy_localizzy.formats.i18next_tree import parse, path_key, records, text
from vexy_localizzy.formats.i18next_write import dump

__all__ = ["load", "dump"]


def project(raw: bytes, source_lang: str = "en") -> Catalog:
    units = []
    for key, path, value in records(parse(raw)):
        forms = (
            {category: text(node) for category, node in value.items()}
            if isinstance(value, dict)
            else None
        )
        source = forms["other"] if forms is not None else text(value)
        tokens = dict.fromkeys(
            token
            for entry in (forms.values() if forms is not None else [source])
            for token in re.findall(r"\{\{.*?\}\}", entry, re.DOTALL)
        )
        units.append(
            Unit(
                key=key,
                context="",
                source=source,
                plural=PluralForms(forms=forms) if forms is not None else None,
                placeholders=[
                    Placeholder(token=token, style="i18next") for token in tokens
                ],
                record_id=("plural:" if forms is not None else "value:")
                + path_key(path),
            )
        )
    return Catalog(
        source_lang=source_lang,
        units=units,
        origin_format="i18next",
        document=SourceDocument.capture(raw, "i18next"),
    )


def load(path: str | Path, *, source_lang: str = "en") -> Catalog:
    """Load one resource file; locale and namespace configuration remain external."""
    return project(Path(path).read_bytes(), source_lang)
