# this_file: src/vexy_localizzy/qt/ui.py
"""Qt Designer ``.ui`` reader for the scan engine.

``lupdate`` extracts every ``<string>`` not marked ``notr="true"``. This module
enumerates ``<string>`` properties with their owning widget for context, plus
the embedded-image count a reviewer cares about. It returns plain dataclasses;
``qt.scan`` turns them into findings.
"""

from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

# .ui files come from source trees; never expand entities or touch the network.
_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)


@dataclass(frozen=True)
class UiString:
    text: str
    widget: str  # owning widget name or class, for context
    prop: str  # property name (text/title/toolTip/...)
    notr: bool
    line: int


@dataclass(frozen=True)
class UiFile:
    path: Path
    klass: str | None
    strings: list[UiString] = field(default_factory=list)
    image_count: int = 0


def _ui_string(prop: etree._Element, string: etree._Element) -> UiString:
    owner = prop.getparent()
    widget = (
        (owner.get("name") or owner.get("class") or "") if owner is not None else ""
    )
    return UiString(
        text=string.text or "",
        widget=widget,
        prop=prop.get("name") or "",
        notr=string.get("notr") == "true",
        line=string.sourceline or 0,
    )


def load(path: str | Path) -> UiFile:
    """Parse a ``.ui`` file; malformed XML raises ``lxml.etree.XMLSyntaxError``."""
    path = Path(path)
    root = etree.parse(str(path), _PARSER).getroot()
    class_el = root.find("class")
    strings = [
        _ui_string(prop, string)
        for prop in root.iter("property")
        if (string := prop.find("string")) is not None
    ]
    image_count = sum(1 for _ in root.iter("iconset")) + sum(
        1 for _ in root.iter("pixmap")
    )
    return UiFile(
        path=path,
        klass=class_el.text if class_el is not None else None,
        strings=strings,
        image_count=image_count,
    )
