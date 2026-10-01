# this_file: src/vexy_localizzy/memory/glossary_json.py
"""Derive a compact ``{source term: {code: translation}}`` JSON view from glossary TMX.

Scripts outside localizzy often need the approved terminology as one small
JSON object rather than a set of TMX memories. The memories stay canonical;
this view is regenerated from them and must not be edited by hand. Only units
whose ``x-status`` is selected (approved and do-not-translate by default) and
whose source and target are both non-empty take part. Each memory supplies one
code, which is only the output key: given explicitly, or the memory's single
non-source language tag. The memory's target language is the code's exact tag
when present, else its only non-source language, else the closest regional
variant (``es-419`` for ``es``) as ``translate`` picks it. Terms sort
case-insensitively (a stable sort: tied spellings keep memory order), codes
alphabetically.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from vexy_localizzy.formats.document import atomic_write
from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.direct import read_bilingual
from vexy_localizzy.memory.glossary import DEFAULT_STATUSES
from vexy_localizzy.memory.langmatch import select_language
from vexy_localizzy.memory.tmx_read import read_tmx

CODE_FIELD = "{code}"


def memory_paths(
    folder: Path, pattern: str, codes: Sequence[str]
) -> list[tuple[str, Path]]:
    """``(code, folder / pattern-with-code)`` for each code; pattern holds ``{code}``."""
    if CODE_FIELD not in pattern:
        raise ValueError(f"pattern must contain {CODE_FIELD}: {pattern!r}")
    if not codes:
        raise ValueError("a folder needs at least one language code")
    return [(code, Path(folder) / pattern.replace(CODE_FIELD, code)) for code in codes]


def target_language(path: Path, source_lang: str, code: str | None = None) -> str:
    """The TUV language of ``path`` that answers for ``code``.

    The exact tag, else the only non-source language, else the closest regional
    variant; ValueError names the candidates when none or several fit.
    """
    languages = {s.language for unit in read_tmx(path) for s in unit.segments}
    if not languages:
        raise ValueError(f"{path} has no translation units")
    source = select_language(languages, source_lang, strict=False)
    others = sorted(languages - {source})
    exact = [tag for tag in others if code and tag == canonical_locale(code)]
    if exact or len(others) == 1:
        return (exact or others)[0]
    if code and others:
        try:
            return select_language(others, code)
        except ValueError:
            pass
    wanted = f"for {code!r} " if code else ""
    raise ValueError(
        f"{path}: no single target language {wanted}among {others}; "
        "pass a code that names one"
    )


def read_terms(
    path: Path,
    *,
    source_lang: str,
    target_lang: str,
    statuses: frozenset[str] = DEFAULT_STATUSES,
) -> dict[str, str]:
    """Source term → translation for the selected statuses; a later unit wins.

    ``target_lang`` is the memory's exact tag, as ``target_language`` returns it.
    """
    memory = read_bilingual(
        path, source_lang=source_lang, target_lang=target_lang, memory_lang=target_lang
    )
    terms = {}
    for unit, src, tgt in memory.pairs:
        status = next((v for n, v in unit.properties if n == "x-status"), None)
        if status in statuses and src.text and tgt.text:
            terms[src.text] = tgt.text
    return terms


def build_glossary(
    memories: Sequence[tuple[str | None, Path]],
    *,
    source_lang: str = "en",
    statuses: frozenset[str] = DEFAULT_STATUSES,
) -> dict[str, dict[str, str]]:
    """The sorted JSON view of ``(code or None, path)`` memories."""
    glossary: dict[str, dict[str, str]] = {}
    for code, path in memories:
        tag = target_language(path, source_lang, code)
        code = code or tag
        terms = read_terms(
            path, source_lang=source_lang, target_lang=tag, statuses=statuses
        )
        for source, target in terms.items():
            glossary.setdefault(source, {})[code] = target
    ordered = sorted(glossary.items(), key=lambda kv: kv[0].casefold())
    return {term: dict(sorted(codes.items())) for term, codes in ordered}


def write_glossary_json(
    out: Path,
    memories: Sequence[tuple[str | None, Path]],
    *,
    source_lang: str = "en",
    statuses: frozenset[str] = DEFAULT_STATUSES,
) -> dict:
    """Build the view, write it to ``out`` and return a summary.

    Raises ValueError when ``out`` is one of the memories.
    """
    if not memories:
        raise ValueError("no glossary memories given")
    if Path(out).resolve() in {Path(path).resolve() for _, path in memories}:
        raise ValueError(f"{out} is an input memory; choose another output")
    for _, path in memories:
        if not Path(path).is_file():
            raise FileNotFoundError(f"glossary memory does not exist: {path}")
    glossary = build_glossary(memories, source_lang=source_lang, statuses=statuses)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(glossary, ensure_ascii=False, indent=2) + "\n"
    atomic_write(out, text.encode("utf-8"))
    codes = sorted({code for entry in glossary.values() for code in entry})
    return {
        "out": str(out),
        "terms": len(glossary),
        "codes": codes,
        "memories": [str(path) for _, path in memories],
    }
