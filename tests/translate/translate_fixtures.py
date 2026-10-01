# this_file: tests/translate/translate_fixtures.py
"""Synthetic TS catalogs, TMX memories and a recording fake provider."""

from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from vexy_localizzy.translate.types import TranslationResult


def _has_abersetz() -> bool:
    try:
        import vexy_localizzy.translate.abersetz_transport  # noqa: F401
    except ImportError:
        return False
    return True


# The cache identity names the abersetz transport, so engine paths need the extra.
needs_abersetz = pytest.mark.skipif(
    not _has_abersetz(), reason="needs the translation extra (abersetz)"
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "memory"
CORE_DE = FIXTURES / "core-de.tmx"

# English source catalog (no target language yet) for the new-language path.
SOURCE_TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" sourcelanguage="en">
<context>
    <name>Menu</name>
    <message>
        <source>Save</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source>Open</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source>Move %1</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source>Kerning</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source>Glyph kerning for %1</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source></source>
        <translation>keep</translation>
    </message>
    <message>
        <source>Gone</source>
        <translation type="vanished">weg</translation>
    </message>
</context>
<context>
    <name>Files</name>
    <message numerus="yes">
        <source>%n file(s)</source>
        <translation type="unfinished">
            <numerusform></numerusform>
            <numerusform></numerusform>
        </translation>
    </message>
</context>
</TS>
"""

# German catalog: existing finished, unfinished-with-text and empty messages.
GERMAN_TS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="de_DE" sourcelanguage="en">
<context>
    <name>Menu</name>
    <message>
        <location filename="menu.cpp" line="10"/>
        <source>Save</source>
        <translation>Speichern (vorhanden)</translation>
    </message>
    <message>
        <source>Open</source>
        <translation type="unfinished">Öffnen (Entwurf)</translation>
    </message>
    <message>
        <source>Close %1</source>
        <translation>Schließen</translation>
    </message>
    <message>
        <source>Quit</source>
        <translation type="unfinished"></translation>
    </message>
</context>
</TS>
"""


def tu(context: str, source: str, target: str, *, lang: str = "de", **props) -> str:
    extra = "".join(
        f'<prop type="x-{name.replace("_", "-")}">{escape(value)}</prop>'
        for name, value in props.items()
    )
    form = f":{props['numerus_form']}" if "numerus_form" in props else ""
    return (
        f'<tu tuid="{escape(context)}|{escape(source)}{form}">'
        f'<prop type="x-context">{escape(context)}</prop>{extra}'
        f'<tuv xml:lang="en"><seg>{escape(source)}</seg></tuv>'
        f'<tuv xml:lang="{lang}"><seg>{escape(target)}</seg></tuv></tu>'
    )


def term(source: str, target: str, *, lang: str = "de", **props) -> str:
    """A glossary TU; ``props`` override ``status="approved"``, ``translatable="yes"``."""
    props = {"status": "approved", "translatable": "yes"} | props
    extra = "".join(
        f'<prop type="x-{name}">{escape(value)}</prop>' for name, value in props.items()
    )
    return (
        f'<tu tuid="term:{escape(source)}">{extra}'
        f'<tuv xml:lang="en"><seg>{escape(source)}</seg></tuv>'
        f'<tuv xml:lang="{lang}"><seg>{escape(target)}</seg></tuv></tu>'
    )


def tmx(path: Path, *units: str) -> Path:
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><tmx version="1.4">'
        '<header creationtool="t" creationtoolversion="1" segtype="sentence" '
        'o-tmf="t" adminlang="en" srclang="en" datatype="plaintext"/>'
        f"<body>{''.join(units)}</body></tmx>",
        encoding="utf-8",
    )
    return path


def ui_memory(tmp_path: Path) -> Path:
    """Menu|Save context hit, Open source-only hit, Move %1 fails placeholder QA,
    and the 2-form numerus message."""
    return tmx(
        tmp_path / "ui-de.tmx",
        tu("Menu", "Save", "Sichern"),
        tu("Toolbar", "Open", "Öffnen"),
        tu("Dialog", "Open", "Öffnen"),
        tu("Menu", "Move %1", "Verschieben"),
        tu("Files", "%n file(s)", "%n Datei", numerus_form="0"),
        tu("Files", "%n file(s)", "%n Dateien", numerus_form="1"),
    )


class FakeProvider:
    """Deterministic provider that records every batch it receives."""

    def __init__(self) -> None:
        self.batches = []

    def __call__(self, model, batch):
        self.batches.append(batch)
        return TranslationResult(
            targets={item.id: "DE " + item.source for item in batch.items},
            requested_model=model,
            reported_model=model + "-reported",
        )

    @property
    def sources(self) -> list[str]:
        return [item.source for batch in self.batches for item in batch.items]


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path
