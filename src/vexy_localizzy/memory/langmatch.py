# this_file: src/vexy_localizzy/memory/langmatch.py
"""Choose which TUV language of a memory answers for a catalog language.

Catalogs say ``de_DE`` or ``es_MX``; memories say ``de`` or ``es-419``. Exact tag
equality would find nothing, so a same-primary-language fallback is explicit here.
The fallback never crosses a script (zh-Hans for zh-TW, sr-Latn for sr-Cyrl) or
the Brazilian/European Portuguese line, and never accepts a regional variant
further away than ``MAX_DISTANCE`` (es-ES for es-MX, en for en-GB).
"""

from collections.abc import Iterable

import langcodes

from vexy_localizzy.locales import canonical_locale

# langcodes.tag_distance: 0-3 same, 4 minor regional (de-CH for de), 5 and up
# a variant a reader notices (es-ES for es-MX, en for en-GB, pt-BR for pt-PT).
MAX_DISTANCE = 4
_PORTUGUESE_SPLIT = frozenset({"BR", "PT"})


def _compatible(target: str, candidate: str) -> bool:
    """Same maximized script, and not Brazilian against European Portuguese."""
    want = langcodes.Language.get(target).maximize()
    have = langcodes.Language.get(candidate).maximize()
    if want.script != have.script:
        return False
    return not (
        want.language == "pt" and {want.territory, have.territory} == _PORTUGUESE_SPLIT
    )


def select_language(
    available: Iterable[str],
    wanted: str,
    *,
    override: str | None = None,
    strict: bool = True,
) -> str:
    """Pick the TUV language to read from a bilingual memory.

    1. override given → its canonical form must be in `available`, else ValueError.
    2. canonical_locale(wanted) exactly in available → it.
    3. same primary language subtag, same script, no pt-BR/pt-PT cross, and
       langcodes.tag_distance ≤ MAX_DISTANCE: the unique closest one; a tie →
       ValueError listing them.
    4. none → ValueError naming the wanted tag; pass --memory-lang.

    ``strict=False`` drops the script, Portuguese and distance limits in step 3
    (used for the source side, where the match is verbatim on the text anyway).
    """
    tags = sorted({canonical_locale(tag) for tag in available})
    if override is not None:
        chosen = canonical_locale(override)
        if chosen not in tags:
            raise ValueError(
                f"memory has no {override} variant (has {', '.join(tags)})"
            )
        return chosen
    target = canonical_locale(wanted)
    if target in tags:
        return target
    primary = langcodes.Language.get(target).language
    same = [t for t in tags if langcodes.Language.get(t).language == primary]
    distances = {t: langcodes.tag_distance(target, t) for t in same}
    if strict:
        same = [
            t for t in same if _compatible(target, t) and distances[t] <= MAX_DISTANCE
        ]
    if not same:
        raise ValueError(f"memory has no {wanted} variant; pass --memory-lang")
    best = min(distances[t] for t in same)
    closest = [t for t in same if distances[t] == best]
    if len(closest) > 1:
        raise ValueError(
            f"memory has several equally close {wanted} variants "
            f"({', '.join(closest)}); pass --memory-lang"
        )
    return closest[0]
