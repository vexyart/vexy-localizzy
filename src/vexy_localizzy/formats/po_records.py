# this_file: src/vexy_localizzy/formats/po_records.py
"""Gettext parsing and projection through the published polib API."""

import copy
import io
import re
import tempfile
import tokenize

import polib

from vexy_localizzy.catalog import (
    Catalog,
    PluralForms,
    Unit,
    derive_key,
    detect_placeholders,
)
from vexy_localizzy.formats.document import SourceDocument
from vexy_localizzy.formats.po_plural import complete, plural_count


def parse(raw: bytes) -> polib.POFile:
    # polib accepts either paths or content strings. A private temporary path
    # prevents malformed content from accidentally being treated as a filename.
    with tempfile.NamedTemporaryFile(suffix=".po") as stream:
        stream.write(raw)
        stream.flush()
        encoding = polib.detect_encoding(stream.name)
        check_quotes(raw.decode(encoding))
        return polib.pofile(stream.name, wrapwidth=0)


def check_quotes(text: str) -> None:
    """Reject truncated literals that polib otherwise silently slices shorter."""
    field = re.compile(r"^(?:msgctxt|msgid(?:_plural)?|msgstr(?:\[\d+\])?)\s+")
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip().removeprefix("#~ ").removeprefix("#| ")
        value = field.sub("", line, count=1)
        if value == line and not line.startswith('"'):
            continue
        try:
            tokens = [
                token
                for token in tokenize.generate_tokens(io.StringIO(value).readline)
                if token.type not in (tokenize.NEWLINE, tokenize.ENDMARKER)
            ]
            valid = (
                len(tokens) == 1
                and tokens[0].type == tokenize.STRING
                and tokens[0].string == value
                and value.startswith('"')
                and value.endswith('"')
                and not value.startswith('"""')
            )
        except (tokenize.TokenError, IndentationError):
            valid = False
        if not valid:
            raise ValueError(f"Invalid PO string literal at line {number}")


def project(raw: bytes, source_lang: str | None = None) -> Catalog:
    parsed = parse(raw)
    try:
        count = plural_count(parsed.metadata.get("Plural-Forms", ""))
    except ValueError:
        count = None
    units, used = [], set()
    for index, entry in enumerate(parsed):
        context = entry.msgctxt or ""
        key = derive_key(context, entry.msgid)
        while key in used:
            key += f"~{index}"
        used.add(key)
        plural = (
            PluralForms(
                indexing="index",
                forms={str(i): text for i, text in entry.msgstr_plural.items()},
            )
            if entry.msgid_plural
            else None
        )
        translated = (
            complete(entry, count) if plural is not None else bool(entry.msgstr)
        )
        state = (
            "vanished"
            if entry.obsolete
            else "needs_review"
            if "fuzzy" in entry.flags
            else "translated"
            if translated
            else "untranslated"
        )
        units.append(
            Unit(
                key=key,
                record_id=f"po:{index}",
                source=entry.msgid,
                source_plural=entry.msgid_plural or None,
                context=context,
                target=entry.msgstr if plural is None else None,
                plural=plural,
                state=state,
                notes=[note for note in (entry.tcomment, entry.comment) if note],
                locations=[
                    f"{file}:{line}" if line else file
                    for file, line in entry.occurrences
                ],
                placeholders=detect_placeholders(entry.msgid),
            )
        )
    return Catalog(
        source_lang=source_lang or parsed.metadata.get("X-Source-Language", "en"),
        target_lang=parsed.metadata.get("Language"),
        units=units,
        origin_format="po",
        document=SourceDocument.capture(raw, "po"),
    )


def serialize(parsed: polib.POFile) -> bytes:
    """Use polib's serializer while retaining obsolete/active entry order."""
    header = copy.copy(parsed)
    header[:] = []
    text = (
        str(header)
        + "\n"
        + "\n".join(entry.__unicode__(wrapwidth=0) for entry in parsed)
    )
    raw = text.encode(parsed.encoding)
    recovered = parse(raw)
    if metadata(parsed) != metadata(recovered):
        raise ValueError("PO serialization would lose metadata")
    return raw


def metadata(parsed: polib.POFile) -> dict:
    """All parser-exposed semantics, excluding source line positions/encoding aliases."""
    return {
        "header": parsed.header,
        "metadata": parsed.metadata,
        "metadata_is_fuzzy": bool(parsed.metadata_is_fuzzy),
        "entries": [
            {
                key: value
                for key, value in vars(entry).items()
                if key not in {"linenum", "encoding"}
            }
            for entry in parsed
        ],
    }
