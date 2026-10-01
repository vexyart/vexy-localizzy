# this_file: src/vexy_localizzy/memory/names.py
"""Optional legacy TMX filename policy, separate from canonical locale identity.

This is a naming convention: choosing the most populous territory as the bare
language does not make regional translations equivalent. This module plans only;
callers control filesystem changes. Adapted from earlier tooling; see NOTICE.
"""

from collections import defaultdict
from functools import cache
from pathlib import Path

from langcodes import Language, LanguageTagError
from language_data.population_data import LANGUAGE_SPEAKING_POPULATION
from loguru import logger

SCRIPT_EXPLICIT = {"zh"}


def parse_tag(
    stem: str, *, territory_aliases: dict[str, str] | None = None
) -> Language | None:
    """Parse a filename tag; optional historical territory aliases are caller policy."""
    try:
        lang = Language.get(stem, normalize=True)
    except LanguageTagError:
        return None
    aliases = {
        key.upper(): value.upper() for key, value in (territory_aliases or {}).items()
    }
    if lang.territory in aliases:
        lang = Language.get(
            str(lang.update_dict({"territory": aliases[lang.territory]}))
        )
    return lang if lang.language and lang.is_valid() else None


def normalize_script(lang: Language) -> Language:
    """Spell out the script for SCRIPT_EXPLICIT languages, else drop it if redundant."""
    if lang.language in SCRIPT_EXPLICIT:
        return lang.update_dict({"script": lang.maximize().script})
    if not lang.script:
        return lang
    base = Language.make(language=lang.language, territory=lang.territory)
    if base.maximize().script == lang.script:
        return lang.update_dict({"script": None})
    return lang


@cache
def top_territory(language: str, script: str | None = None) -> str | None:
    """Territory with the most speakers of ``language`` per CLDR, if unique.

    With ``script``, only territories whose likely script matches are ranked.
    """
    prefix = f"{language}-"
    ranked = sorted(
        (
            (pop, tag[len(prefix) :])
            for tag, pop in LANGUAGE_SPEAKING_POPULATION.items()
            if tag.startswith(prefix)
            and (script is None or Language.get(tag).maximize().script == script)
        ),
        reverse=True,
    )
    if not ranked or ranked[0][0] <= 0:
        return None
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        logger.warning(
            f"{language}: CLDR population tie between {ranked[0][1]} and {ranked[1][1]}"
        )
        return None
    return ranked[0][1]


def drop_top_territory(lang: Language) -> Language:
    """Remove the territory subtag if it is the top territory for the language.

    The territory is kept when dropping it would change the implied script
    (``pa-PK`` implies Arabic, bare ``pa`` implies Gurmukhi; ``yue-CN`` implies
    Simplified, bare ``yue`` implies Traditional).
    """
    script = lang.script if lang.language in SCRIPT_EXPLICIT else None
    if not (
        lang.territory
        and lang.language
        and lang.territory == top_territory(lang.language, script)
    ):
        return lang
    shorter = lang.update_dict({"territory": None})
    if shorter.maximize().script != lang.maximize().script:
        return lang
    return shorter


def plan_folder(
    files: list[Path], *, territory_aliases: dict[str, str] | None = None
) -> list[tuple[Path, str | None, str]]:
    """Return (path, new_name_or_None, note) for every .tmx in one folder."""
    if len({path.parent for path in files}) > 1:
        raise ValueError("Filename planning requires paths from one folder")
    plan: dict[Path, tuple[str | None, str]] = {}
    for path in files:
        lang = parse_tag(path.stem, territory_aliases=territory_aliases)
        if lang is None:
            plan[path] = (None, "not a valid tag, skipped")
            continue
        lang = drop_top_territory(normalize_script(lang))
        plan[path] = (f"{str(lang).lower()}.tmx", "")

    targets: dict[str, list[Path]] = defaultdict(list)
    for path, (new_name, _) in plan.items():
        if new_name:
            targets[new_name].append(path)
    for new_name, paths in targets.items():
        if len(paths) > 1:
            for path in paths:
                plan[path] = (None, f"collision: {len(paths)} files -> {new_name}")

    return [(p, n, note) for p, (n, note) in sorted(plan.items())]
