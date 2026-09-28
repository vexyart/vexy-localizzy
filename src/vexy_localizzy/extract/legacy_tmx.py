# this_file: src/vexy_localizzy/extract/legacy_tmx.py
"""Legacy row-to-TMX writer of the po2tmx/ts2tmx/oss2tmx converters.

Rows are ``(src, tgt, ctx, plural[, origin])``. Text is cleaned of XML-illegal
characters, empty and repeated ``(src, tgt, ctx)`` rows are dropped, and tuids
number the kept rows from 1. Publication is atomic via ``tmx_writer``.
"""

from collections.abc import Iterable, Iterator
from pathlib import Path

from vexy_localizzy.extract.legacy_lang import clean_text
from vexy_localizzy.memory.tmx_write import TMXRecord, write_records


def write_tmx(
    path: Path,
    src_lang: str,
    tgt_lang: str,
    origin: str,
    rows: Iterable[tuple],
    tool: str = "po2tmx",
    origin_format: str = "gettext",
) -> int:
    """Write selected rows; a row's fifth field overrides ``origin``. Return the unit count.

    The header defaults reproduce the legacy files, which ts2tmx and oss2tmx
    also wrote through po2tmx's writer.
    """

    def records() -> Iterator[TMXRecord]:
        seen: set[tuple[str, str, str | None]] = set()
        for src, tgt, ctx, plural, *extra in rows:
            src, tgt = clean_text(src), clean_text(tgt)
            signature = (src, tgt, ctx)
            if not src or not tgt or signature in seen:
                continue
            seen.add(signature)
            properties = [("x-origin", extra[0] if extra else origin)]
            if ctx:
                properties.append(("x-context", clean_text(ctx)))
            if plural:
                properties.append(("x-plural", plural))
            yield TMXRecord(
                str(len(seen)), ((src_lang, src), (tgt_lang, tgt)), tuple(properties)
            )

    return write_records(
        path,
        records(),
        source_lang=src_lang,
        creation_tool=tool,
        origin_format=origin_format,
    )
