# this_file: src/vexy_localizzy/tmx.py
"""Streaming multilingual TMX records with stable source occurrence ordinals."""

import gzip
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.xmlio import records

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


class UnitError(ValueError):
    """A structural unit error with its original occurrence ordinal."""

    def __init__(self, ordinal: int, message: str) -> None:
        self.ordinal = ordinal
        super().__init__(f"TU {ordinal}: {message}")


@dataclass(frozen=True)
class Segment:
    """Plain text and namespace-normalized XML; raw bytes remain in source snapshots."""

    language: str
    raw_language: str
    text: str
    xml: str
    inline: bool
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Unit:
    """One immutable TU; ordinal refers to its position in the source file."""

    ordinal: int
    tuid: str
    source_language: str
    properties: tuple[tuple[str, str], ...]
    segments: tuple[Segment, ...]
    notes: tuple[str, ...] = ()

    def english(self) -> Segment | None:
        """Select explicitly tagged English, never positional source guesses."""
        choices = [s for s in self.segments if s.language.split("-")[0] == "en"]
        if not choices:
            return None
        preferred = (
            self.source_language if self.source_language.startswith("en") else "en"
        )
        exact = [s for s in choices if s.language == preferred]
        choices = exact or choices
        if len({s.text for s in choices}) != 1:
            raise ValueError(f"Ambiguous English source at TU {self.ordinal}")
        return choices[0]


def _notes(element: etree._Element, namespace: str) -> tuple[str, ...]:
    """Direct-child <note> texts only; header notes arrive as separate records."""
    return tuple("".join(n.itertext()) for n in element.findall(namespace + "note"))


def _segment(tuv: etree._Element, namespace: str) -> Segment:
    raw = tuv.get(XML_LANG) or tuv.get("lang")
    if not raw:
        raise ValueError("TMX variant is missing its language")
    segment = tuv.find(namespace + "seg")
    if segment is None:
        raise ValueError("TMX variant is missing its segment")
    segment = deepcopy(segment)
    if namespace:
        for node in segment.iter():
            if isinstance(node.tag, str) and node.tag.startswith(namespace):
                node.tag = node.tag[len(namespace) :]
        etree.cleanup_namespaces(segment)
    return Segment(
        language=canonical_locale(raw),
        raw_language=raw,
        text="".join(segment.itertext()),
        xml=etree.tostring(segment, encoding="unicode", with_tail=False),
        inline=len(segment) > 0,
        notes=_notes(tuv, namespace),
    )


def read_tmx(path: str | Path) -> Iterator[Unit]:
    """Read units lazily; malformed XML and unsupported entities fail explicitly."""
    source, ordinal = "", 0
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        for kind, element, namespace in records(stream):
            if kind == "root" and etree.QName(element).localname != "tmx":
                raise ValueError("Expected a TMX root")
            if kind == "header":
                source = element.get("srclang", "")
            if kind != "tu":
                continue
            ordinal += 1
            declared = element.get("srclang", source)
            try:
                if declared and declared != "*all*":
                    declared = canonical_locale(declared)
                yield Unit(
                    ordinal,
                    element.get("tuid", ""),
                    declared,
                    tuple(
                        (p.get("type", ""), "".join(p.itertext()))
                        for p in element.findall(namespace + "prop")
                    ),
                    tuple(
                        _segment(tuv, namespace)
                        for tuv in element.findall(namespace + "tuv")
                    ),
                    _notes(element, namespace),
                )
            except ValueError as error:
                raise UnitError(ordinal, str(error)) from error
