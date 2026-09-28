#!/usr/bin/env -S uv run -s
# /// script
# dependencies = ["vexy-localizzy"]
# ///
# this_file: examples/review_sample.py
"""Create a new, synthetic eight-message review workspace; never overwrite one."""

import argparse
import json
from pathlib import Path

from vexy_localizzy.formats import json_io, ts

CATALOG = """<?xml version="1.0" encoding="utf-8"?>
<TS version="2.1" language="pl" sourcelanguage="en">
<context><name>FileDialog</name>
<message id="open"><source>Open file</source><extracomment>Button label in the file dialog.</extracomment><translation type="unfinished">Otwórz</translation></message>
<message id="save"><source>Save changes</source><translation>Zapisz zmiany</translation></message>
<message id="cancel"><source>Cancel</source><translation>Anuluj</translation></message>
</context>
<context><name>Properties</name>
<message id="width"><source>Width</source><translation type="unfinished">Szerokość</translation></message>
<message id="height"><source>Height</source><translation type="unfinished">Wysokość</translation></message>
</context>
<context><name>ListView</name>
<message id="items" numerus="yes"><source>%n items</source><translation type="unfinished"><numerusform>%n element</numerusform><numerusform>%n elementy</numerusform><numerusform>%n elementów</numerusform></translation></message>
</context>
<context><name>Application</name>
<message id="help"><source>Help</source><translation type="unfinished">Pomoc</translation></message>
</context>
<context><name>FileDialog</name>
<message id="close"><source>Close</source><translation type="unfinished">Zamknij</translation></message>
</context></TS>
"""

UI = """<?xml version="1.0" encoding="utf-8"?>
<ui version="4.0"><class>FileDialog</class>
<widget class="QDialog" name="FileDialog">
<property name="geometry"><rect><x>0</x><y>0</y><width>430</width><height>210</height></rect></property>
<property name="windowTitle"><string>File</string></property>
<widget class="QLabel" name="nameLabel"><property name="geometry"><rect><x>18</x><y>22</y><width>390</width><height>24</height></rect></property><property name="text"><string>Name</string></property></widget>
<widget class="QLineEdit" name="name"><property name="geometry"><rect><x>18</x><y>50</y><width>394</width><height>36</height></rect></property><property name="text"><string>Untitled</string></property></widget>
<widget class="QPushButton" name="open"><property name="geometry"><rect><x>172</x><y>113</y><width>128</width><height>40</height></rect></property><property name="text"><string>Open file</string></property></widget>
<widget class="QPushButton" name="cancel"><property name="geometry"><rect><x>314</x><y>113</y><width>98</width><height>40</height></rect></property><property name="text"><string>Cancel</string></property></widget>
</widget><resources/><connections/></ui>
"""


def create(directory: Path) -> Path:
    """Generate native TS, retained JSON, UI and provenance suggestions together."""
    directory.mkdir(parents=True, exist_ok=False)
    source = directory / "sample.ts"
    source.write_text(CATALOG, encoding="utf-8")
    catalog = ts.load(source)
    units = [
        unit.model_copy(
            update={
                "state": "approved"
                if unit.key in ("id:save", "id:cancel")
                else "needs_review"
                if unit.key == "id:open"
                else "untranslated"
            }
        )
        for unit in catalog.units
    ]
    json_io.dump(
        catalog.model_copy(update={"units": units}), directory / "catalog.json"
    )
    (directory / "sample.ui").write_text(UI, encoding="utf-8")
    (directory / "suggestions.json").write_text(
        json.dumps(
            {
                "sample": {
                    "id:open": [
                        {
                            "source": "Open",
                            "target": "Otwórz",
                            "provenance": "Memory · sample:1",
                        }
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    config = directory / "review.toml"
    config.write_text(
        'root = "."\nsuggestions = "suggestions.json"\n[catalogs]\nsample = "catalog.json"\n[ui_files]\nsample = "sample.ui"\n[plural_forms]\nsample = ["0", "1", "2"]\n',
        encoding="utf-8",
    )
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New workspace directory")
    print(create(parser.parse_args().directory))
