# this_file: tests/extract/legacy_builders.py
"""Deterministic synthetic Adobe folders and Apple bundles for legacy converter tests.

Binary resources (idrc_PMST tables, Pascal-string resource forks, Mach-O stubs,
UTF-16 dictionaries, binary loctables) are built here with ``struct``/``plistlib``
so the golden capture script and the parity tests read identical inputs.
"""

import plistlib
import struct
from pathlib import Path

MACHO_MAGIC = b"\xcf\xfa\xed\xfe"


def pmst(locale_id: int, pairs: list[tuple[str, str]], encoding: int = 8) -> bytes:
    """Encode an InDesign ``idrc_PMST`` string table."""
    body = b""
    for key, value in pairs:
        for field in (key.encode(), value.encode()):
            body += struct.pack("<H", len(field)) + field
    return struct.pack("<III", locale_id, encoding, len(pairs)) + body


def _write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    path.write_bytes(data)


def build_adobe(root: Path) -> Path:
    """Create a synthetic Adobe app folder covering every legacy source kind."""
    res = root / "Plug-ins/Core.InDesignPlugin/Resources/idrc_PMST"
    _write(
        res / "300.idrc",
        pmst(
            1,
            [
                ("kOpen", "Open"),
                ("kSave", "Save^n^C"),
                ("kEmpty", ""),
                ("kSpace", "  "),
            ],
        ),
    )
    _write(
        res / "301.idrc",
        pmst(
            3,
            [
                ("kOpen", "Öffnen"),
                ("kSave", "Speichern^n^C"),
                ("kBell", "Glocke\x01"),
                ("kOnly", "Nur ^0 und ^9 ^x"),
            ],
        ),
    )
    _write(res / "1302.idrc", pmst(99, [("kOpen", "Unknown")]))
    _write(
        res / "302.idrc",
        pmst(2, [("kOpen", "Open"), ("kColour", "Colour")], encoding=0),
    )
    _write(root / "en.lproj/Localizable.strings", '"Hello" = "Hello"; "Same" = "Same";')
    _write(
        root / "de.lproj/Localizable.strings",
        '"Hello" = "Hallo"; "Press the button" = "Drücken Sie die Taste"; "Same" = "Same"; "Only key" = "Nur Schlüssel";',
    )
    _write(root / "de.lproj/InfoPlist.strings", '"CFBundleName" = "Beispiel";')
    _write(root / "pseudo.lproj/Localizable.strings", '"Hello" = "[Ħęľľő]";')
    _write(
        root / "UXP/panel/locale/en_US/strings.json",
        '{"menu":{"open":"Open","id":"menu-1","help":"https://x.test/a"},"title":"Title"}',
    )
    _write(
        root / "UXP/panel/locale/de_DE/strings.json",
        '{"menu":{"open":"Öffnen","id":"menu-1"},"title":"Titel"}',
    )
    _write(
        root / "UXP/panel/locale/en_US/messages.properties",
        "greeting=Hello!\nfarewell=Bye\n",
    )
    _write(
        root / "UXP/panel/locale/de_DE/messages.properties",
        "greeting=Hallo\\u0021\nfarewell=Tsch\\u00fcss\n",
    )
    _write(
        root / "Support/strings.str",
        '$$$/App/Open=Datei ^1 &öffnen\n$$$/App/Tab=A^tB^^C^r\n$$$/App/Quote=Say \\"hi\\"\n$$$/Bad Key!{=Skip\n',
    )
    pascal = b"$$$/Rsrc/Key=Rsrc value"
    _write(
        root / "Support/menu.rsrc",
        b"\x00\x00" + bytes([len(pascal)]) + pascal + b"\x01\x02",
    )
    _write(
        root / "Support/Binary",
        MACHO_MAGIC
        + b"\x00" * 12
        + b"$$$/Bin/Open=Binaer\x00junk($$$/Bin/Paren=Paren (x) value) tail\x00",
    )
    _write(
        root / "Support/tw10428_de_DE.dat",
        '"$$$/TW/Open=TW Öffnen"\r\n"$$$/TW/Esc=Line\\"q\\""\r\n'.encode("utf-16"),
    )
    _write(root / "node_modules/x/de.lproj/Localizable.strings", '"Hello" = "Skip";')
    (root / "Locales/fr_FR").mkdir(parents=True, exist_ok=True)
    return root


def _stringsdict(forms: dict[str, str]) -> bytes:
    rule = {
        "NSStringFormatSpecTypeKey": "NSStringPluralRuleType",
        "NSStringFormatValueTypeKey": "d",
        **forms,
    }
    return plistlib.dumps(
        {"items": {"NSStringLocalizedFormatKey": "%#@n@", "n": rule}}, sort_keys=False
    )


def build_lproj(root: Path) -> Path:
    """Create a synthetic ``.app`` bundle with lproj folders, stringsdicts and a loctable."""
    res = root / "Contents/Resources"
    _write(
        res / "en.lproj/Localizable.strings",
        '"open" = "Open"; "open_again" = "Open"; "save" = "Save"; "same" = "Same";',
    )
    _write(
        res / "Base.lproj/Localizable.strings",
        '"open" = "Base Open"; "base_only" = "Base only";',
    )
    _write(
        res / "German.lproj/Localizable.strings",
        '"open" = "Öffnen"; "save" = "Sichern"; "same" = "Same"; "Press the button" = "Drücken"; "nokey" = "Kein Englisch";',
    )
    _write(res / "German.lproj/InfoPlist.strings", '"CFBundleName" = "Beispiel";')
    _write(
        res / "fr.lproj/Localizable.strings",
        '"open" = "Ouvrir"; "open_again" = "Ouvrir"; "base_only" = "Base seulement";',
    )
    _write(
        res / "en.lproj/Localizable.stringsdict",
        _stringsdict({"one": "%d file", "other": "%d files"}),
    )
    _write(
        res / "pl.lproj/Localizable.stringsdict",
        _stringsdict({"one": "%d plik", "few": "%d pliki", "other": "%d plików"}),
    )
    _write(
        res / "Settings.loctable",
        plistlib.dumps(
            {
                "en": {"title": "Settings"},
                "de": {"title": "Einstellungen"},
                "zh_Hans": {"title": "设置"},
                "LocProvenance": {"title": "ignore"},
            },
            fmt=plistlib.FMT_BINARY,
            sort_keys=False,
        ),
    )
    _write(res / "loose.strings", '"open" = "Loose";')
    _write(root / "Contents/_CodeSignature/de.lproj/x.strings", '"open" = "Skip";')
    return root
