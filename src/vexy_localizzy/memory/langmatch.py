# this_file: src/vexy_localizzy/memory/langmatch.py
"""Choose which TUV language of a memory answers for a catalog language.

Catalogs say ``de_DE`` or ``es_MX``; memories say ``de`` or ``es-419``. Exact tag
equality would find nothing, so a same-primary-language fallback is explicit here.
"""

from collections.abc import Iterable

import langcodes

from vexy_localizzy.locales import canonical_locale


def select_language(
    available: Iterable[str], wanted: str, *, override: str | None = None
) -> str:
    """Pick the TUV language to read from a bilingual memory.

    1. override given → its canonical form must be in `available`, else ValueError.
    2. canonical_locale(wanted) exactly in available → it.
    3. same primary language subtag: one candidate → it; several → the unique
       closest by langcodes.tag_distance; a tie → ValueError listing them.
    4. none → ValueError naming the wanted tag.
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
    if len(same) == 1:
        return same[0]
    if not same:
        raise ValueError(f"memory has no {wanted} variant; pass --memory-lang")
    distances = {t: langcodes.tag_distance(target, t) for t in same}
    best = min(distances.values())
    closest = [t for t in same if distances[t] == best]
    if len(closest) > 1:
        raise ValueError(
            f"memory has several equally close {wanted} variants "
            f"({', '.join(closest)}); pass --memory-lang"
        )
    return closest[0]
