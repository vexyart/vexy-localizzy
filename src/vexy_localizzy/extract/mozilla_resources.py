# this_file: src/vexy_localizzy/extract/mozilla_resources.py
"""Mozilla DTD/properties projections using the published localization parser."""

from moz.l10n.model import Entry, Format, PatternMessage
from moz.l10n.resource import parse_resource


def _unicode_text(text: str) -> str:
    """Join decoded UTF-16 pairs and reject isolated surrogate code points."""
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le")


def parse_mozilla(text: str, kind: str) -> list[tuple[str, str]]:
    """Return ordered pairs; DTD includes remain references and are never fetched.

    Properties escapes are decoded; DTD entity-reference spelling stays literal.
    Duplicate and empty values remain available for caller-owned selection.
    Finish parsing before returning so malformed input cannot publish a subset.
    """
    if kind not in {"dtd", "properties"}:
        raise ValueError(f"Unsupported Mozilla format: {kind}")
    resource = parse_resource(
        {"dtd": Format.dtd, "properties": Format.properties}[kind], text
    )
    pairs = []
    for section in resource.sections:
        for entry in section.entries:
            if not isinstance(entry, Entry):
                continue
            if len(entry.id) != 1 or not isinstance(entry.value, PatternMessage):
                raise ValueError("Expected a flat Mozilla resource entry")
            if not all(isinstance(part, str) for part in entry.value.pattern):
                raise ValueError("Expected literal Mozilla resource text")
            pairs.append(
                (
                    _unicode_text(entry.id[0]),
                    _unicode_text("".join(entry.value.pattern)),
                )
            )
    return pairs
