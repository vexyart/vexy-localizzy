# this_file: src/vexy_localizzy/extract/adobe.py
"""Extract UI localization strings from a macOS Adobe app folder into TMX files.

Sources discovered by walking the input folder:

* InDesign ``idrc_PMST`` string tables (ODFRC ``StringTable`` binaries):
  ``<u32 locale_id><u32 encoding><u32 count>`` then ``count`` pairs of
  ``<u16 len><bytes>`` key / value. Encoding 8 is UTF-8. Locale ids follow the
  InDesign SDK ``PMLocaleIds.h``.
* ZStrings ``$$$/Path/Key=Text`` in ``.str``/``.eve``/``.adm``/``.mnu`` text,
  ``.rsrc`` resource forks (Pascal strings), Photoshop ``tw10428_*.dat``
  dictionaries (UTF-16) and Mach-O executables. Their language is the app's
  installed UI language, auto-detected or given with ``ui_lang``.
* Apple ``.strings`` files inside ``<lang>.lproj`` folders.
* UXP/CEP ``locale/<lang>/**/*.json`` and ``*.properties`` files.

Each ``<lang>.tmx`` pairs the English text of a key with the target text;
``en.tmx`` is monolingual. Keys go to ``tuid``, the table to ``x-domain`` and
the file to ``x-origin``. Adobe caret escapes are decoded (``^n``/``^r`` line
break, ``^t`` tab, ``^C``/``^R``/``^T`` symbols, ``^0``..``^9`` to ``%0``..``%9``,
``^^`` to ``^``). Ported from fl10n ``tools/adobe2tmx.py``.
"""

import os
import re
import struct
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from vexy_localizzy.apple_resources import resource_items
from vexy_localizzy.extract.legacy_lang import PIVOT, XML_BAD, clean_text, norm_lang
from vexy_localizzy.json_resources import string_pairs as json_pairs
from vexy_localizzy.memory.tmx_write import TMXRecord, write_records
from vexy_localizzy.properties_resources import parse_properties as properties_pairs

__all__ = [
    "PIVOT",
    "XML_BAD",
    "Entry",
    "build_tables",
    "clean_text",
    "extract",
    "json_pairs",
    "norm_lang",
    "parse_apple_strings",
    "parse_locale_json",
    "parse_pmst",
    "parse_properties",
    "properties_pairs",
    "rel",
    "run",
    "write_tmx",
]
MAX_BINARY_BYTES = 1_500_000_000

# InDesign SDK PMLocaleIds.h UI language ids, verified against InDesign 2026.
IDRC_LOCALES = {
    1: "en",
    2: "en-GB",
    3: "de",
    4: "fr",
    5: "ja",
    6: "es",
    7: "pt-BR",
    8: "sv",
    9: "da",
    10: "nl",
    11: "it",
    12: "nb",
    13: "fi",
    14: "el",
    15: "cs",
    16: "pl",
    18: "hu",
    19: "ru",
    22: "tr",
    23: "ro",
    30: "uk",
    31: "he",
    32: "ar",
    33: "zh-CN",
    34: "zh-TW",
    35: "ko",
}

ZSTRING_TEXT_EXTS = {".str", ".eve", ".adm", ".mnu", ".TEXT"}
LOCALE_DIR_NAMES = {"locale", "locales", "cmdn-locale"}
SKIP_DIR_PARTS = (
    "Chromium Embedded Framework",
    "CEPHtmlEngine",
    "_CodeSignature",
    "node_modules",
)
MACHO_MAGICS = {
    b"\xcf\xfa\xed\xfe",
    b"\xce\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xfe\xed\xfa\xcf",
    b"\xfe\xed\xfa\xce",
}

ZS_KEY = rb"\$\$\$/([^\x00=\r\n\"]{1,300})="
ZS_BIN_RE = re.compile(ZS_KEY + rb"([^\x00]*)")
ZS_KEY_OK = re.compile(r"[\w][\w ./:,'()\-+&#@!?%*]*$")


CARET_MAP = {"n": "\n", "r": "\n", "t": "\t", "C": "©", "R": "®", "T": "™", "^": "^"}
CARET_RE = re.compile(r"\^([nrtCRT^0-9])")


def decode_caret(text: str) -> str:
    """Decode Adobe caret escapes; unknown sequences stay as they are."""
    return CARET_RE.sub(lambda m: CARET_MAP.get(m.group(1), "%" + m.group(1)), text)


@dataclass(frozen=True, slots=True)
class Entry:
    domain: str
    key: str
    lang: str
    text: str
    origin: str


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# --------------------------------------------------------------------------- #
# InDesign idrc_PMST
# --------------------------------------------------------------------------- #


def decode_pmst(raw: bytes, encoding: int) -> str:
    if encoding == 8:
        return raw.decode("utf-8")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("mac_roman", errors="replace")


def pmst_string(data: bytes, position: int) -> tuple[bytes, int]:
    """Read one length-prefixed field; a truncated payload is never a full value."""
    if position + 2 > len(data):
        raise ValueError("Truncated PMST string length")
    (length,) = struct.unpack_from("<H", data, position)
    start, end = position + 2, position + 2 + length
    if end > len(data):
        raise ValueError("Truncated PMST string payload")
    return data[start:end], end


def parse_pmst(path: Path, root: Path) -> Iterator[Entry]:
    data = path.read_bytes()
    if len(data) < 12:
        raise ValueError("Truncated PMST header")
    locale_id, encoding, count = struct.unpack_from("<III", data, 0)
    lang = IDRC_LOCALES.get(locale_id)
    if lang is None:
        lang = f"und-x-idrc{locale_id}"
        logger.warning("Unknown idrc locale id {} in {}", locale_id, path)
    plugin = path.parents[1]  # .../Resources/idrc_PMST/NNNN.idrc -> Resources
    group = (int(path.stem) // 100) * 100 if path.stem.isdigit() else path.stem
    domain = f"idrc:{rel(plugin, root)}:{group}"
    origin = rel(path, root)
    pos = 12
    for _ in range(count):
        key, pos = pmst_string(data, pos)
        value, pos = pmst_string(data, pos)
        if not key or not value:
            continue
        yield Entry(
            domain,
            decode_pmst(key, encoding),
            lang,
            decode_pmst(value, encoding),
            origin,
        )


# --------------------------------------------------------------------------- #
# ZStrings ($$$/Key=Value)
# --------------------------------------------------------------------------- #


def zstring_entries(
    matches: Iterator[tuple[bytes, bytes]], lang: str, origin: str
) -> Iterator[Entry]:
    for key_b, val_b in matches:
        key = key_b.decode("utf-8", errors="replace").strip()
        value = val_b.decode("utf-8", errors="replace")
        if not value or not ZS_KEY_OK.match(key):
            continue
        yield Entry("zstring", key, lang, value, origin)


ZS_KEY_RE = re.compile(ZS_KEY)
UNESCAPED_QUOTE = {0x22: re.compile(rb'(?<!\\)"'), 0x27: re.compile(rb"(?<!\\)'")}


def unbalanced_paren(value: bytes) -> int:
    """Index of the first ``)`` that closes a ``(`` opened before ``value``, or -1."""
    depth = 0
    for i, c in enumerate(value):
        if c == 0x28:
            depth += 1
        elif c == 0x29:
            if depth == 0:
                return i
            depth -= 1
    return -1


def zstring_value(data: bytes, key_start: int, value_start: int, text: bool) -> bytes:
    """Value of the ZString whose ``=`` ends at value_start.

    Ends at NUL (and at a line break for text files). A ZString that opens
    right after ``(``, ``'`` or ``"`` (Photoshop terminology blobs, embedded
    script in ``.eve`` dialogs) ends at the matching closer. A value never
    swallows a following ZString.
    """
    stop = re.compile(rb"[\x00\r\n]" if text else rb"\x00").search(data, value_start)
    value = data[value_start : stop.start() if stop else len(data)]
    opener = data[key_start - 1] if key_start > 0 else 0
    if opener == 0x28:
        end = unbalanced_paren(value)
        if end >= 0:
            value = value[:end]
    elif opener in UNESCAPED_QUOTE:
        end = UNESCAPED_QUOTE[opener].search(value)
        if end:
            value = value[: end.start()]
    nested = value.find(b"$$$/")
    if nested >= 0:
        value = value[:nested].rstrip(b" (")
    if text:
        value = value.replace(b'\\"', b'"').replace(b"\\'", b"'")
    return value


def scan_zstrings(data: bytes, text: bool = False) -> Iterator[tuple[bytes, bytes]]:
    for m in ZS_KEY_RE.finditer(data):
        yield m.group(1), zstring_value(data, m.start(), m.end(), text)


def scan_zstrings_rsrc(data: bytes) -> Iterator[tuple[bytes, bytes]]:
    """Classic resource forks hold Pascal strings: length byte precedes the text."""
    for m in re.finditer(rb"\$\$\$/", data):
        start = m.start()
        length = data[start - 1] if start > 0 else 0
        chunk = data[start : start + length]
        after = data[start + length] if start + length < len(data) else 0
        pascal = length > 4 and b"\x00" not in chunk and after < 0x20
        sub = ZS_BIN_RE.match(chunk) if pascal else None
        if sub:
            yield sub.group(1), sub.group(2)
            continue
        key = ZS_KEY_RE.match(data, start)
        if key:
            yield key.group(1), zstring_value(data, start, key.end(), False)


def parse_zstring_file(path: Path, root: Path, lang: str) -> Iterator[Entry]:
    size = path.stat().st_size
    if size > MAX_BINARY_BYTES:
        logger.warning("Skipping oversized file {}", path)
        return
    data = path.read_bytes()
    if path.suffix == ".rsrc":
        matches = scan_zstrings_rsrc(data)
    else:
        matches = scan_zstrings(data, text=path.suffix in ZSTRING_TEXT_EXTS)
    yield from zstring_entries(matches, lang, rel(path, root))


def parse_tw10428(path: Path, root: Path, fallback_lang: str) -> Iterator[Entry]:
    m = re.search(r"_([a-z]{2}_[A-Z]{2})\.dat$", path.name)
    lang = norm_lang(m.group(1)) if m else None
    lang = lang or fallback_lang
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = data.decode("utf-16", errors="replace")
    else:
        text = data.decode("utf-8-sig", errors="replace")
    matches = (
        (k.encode(), v.encode())
        for k, v in re.findall(r'"?\$\$\$/([^=\r\n"]+)=((?:[^"\\\r\n]|\\.)*)"?', text)
    )
    yield from zstring_entries(matches, lang, rel(path, root))


# --------------------------------------------------------------------------- #
# Apple .strings, UXP/CEP json + properties
# --------------------------------------------------------------------------- #


def parse_apple_strings(path: Path, root: Path) -> Iterator[Entry]:
    lang = norm_lang(path.parent.name)
    if lang is None:
        return
    data = path.read_bytes()
    domain = f"strings:{rel(path.parent.parent, root)}:{path.name}"
    origin = rel(path, root)
    pairs = resource_items(data)
    for key, value in pairs:
        if isinstance(value, str) and key and value:
            yield Entry(domain, key, lang, value, origin)


def locale_context(path: Path) -> tuple[str, Path] | None:
    """Return (lang, locale_root_dir) if path sits under locale/<lang>/..."""
    parents = list(path.parents)
    for i, parent in enumerate(parents[1:], start=1):
        if parent.name.lower() in LOCALE_DIR_NAMES:
            lang = norm_lang(parents[i - 1].name)
            return (lang, parent) if lang else None
    return None


JSON_META_KEY = re.compile(
    r"(^|[._-])(id|ids|url|href|src|version|helpx)$|(?<=[a-z])(Id|Ids|Url|URL|ID|Href|Src|Version)$"
)


def translatable_json_value(key: str, value: str) -> bool:
    """Drop identifiers, help paths and other non-UI leaves from locale JSON."""
    last = key.rsplit(".", 1)[-1]
    if JSON_META_KEY.search(last):
        return False
    if not re.search(r"[^\W\d_]", value):
        return False
    return not ("/" in value and " " not in value)


def parse_locale_json(path: Path, root: Path) -> Iterator[Entry]:
    ctx = locale_context(path)
    if ctx is None:
        return
    lang, locale_dir = ctx
    data = path.read_bytes()
    text = data.decode(
        "utf-16" if data[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    )
    pairs = json_pairs(text)
    sub = path.relative_to(locale_dir).as_posix().split("/", 1)[-1]
    domain = f"json:{rel(locale_dir.parent, root)}:{sub}"
    origin = rel(path, root)
    seen = set()
    for parts, value in pairs:
        key = ".".join(map(str, parts))
        if not value.strip() or not translatable_json_value(key, value):
            continue
        if key in seen:
            raise ValueError(f"Ambiguous dotted JSON key: {key}")
        seen.add(key)
        yield Entry(domain, key, lang, value, origin)


def parse_properties(path: Path, root: Path) -> Iterator[Entry]:
    ctx = locale_context(path)
    if ctx is None:
        return
    lang, locale_dir = ctx
    data = path.read_bytes()
    text = data.decode(
        "utf-16" if data[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    )
    sub = path.relative_to(locale_dir).as_posix().split("/", 1)[-1]
    domain = f"properties:{rel(locale_dir.parent, root)}:{sub}"
    origin = rel(path, root)
    for key, value in properties_pairs(text):
        if key and value:
            yield Entry(domain, key, lang, value, origin)


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #


def detect_ui_lang(root: Path) -> str:
    candidates = [root / "Locales", root / "Support Files" / "Resources"]
    for cand in candidates:
        if cand.is_dir():
            for child in sorted(cand.iterdir()):
                lang = norm_lang(child.name)
                if child.is_dir() and lang:
                    logger.info(
                        "Detected installed UI language {} from {}", lang, child
                    )
                    return lang
    for hit in root.rglob("tw10428_*.dat"):
        m = re.search(r"_([a-z]{2}_[A-Z]{2})\.dat$", hit.name)
        lang = norm_lang(m.group(1)) if m else None
        if lang:
            return lang
    logger.info("No installed UI language marker found, assuming en")
    return PIVOT


def is_macho(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(4) in MACHO_MAGICS
    except OSError:
        return False


def classify(path: Path) -> str | None:
    parent = path.parent.name
    suffix = path.suffix
    if parent == "idrc_PMST":
        return "pmst"
    if suffix == ".strings" and path.parent.suffix == ".lproj":
        return "strings"
    if re.match(r"tw10428_.*\.dat$", path.name):
        return "tw10428"
    if suffix == ".json" and locale_context(path):
        return "json"
    if suffix == ".properties":
        return "properties"
    if suffix in ZSTRING_TEXT_EXTS or suffix == ".rsrc":
        return "zstring"
    if suffix == "" and is_macho(path):
        return "zstring"
    return None


def walk_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not any(p in d for p in SKIP_DIR_PARTS)]
        for name in filenames:
            p = Path(dirpath) / name
            if not p.is_symlink() and p.is_file():
                yield p


def extract(
    root: Path, ui_lang: str, include_infoplist: bool
) -> tuple[list[Entry], Counter]:
    entries: list[Entry] = []
    stats: Counter = Counter()
    for path in walk_files(root):
        kind = classify(path)
        if kind is None:
            continue
        if (
            kind == "strings"
            and not include_infoplist
            and path.name == "InfoPlist.strings"
        ):
            continue
        try:
            before = len(entries)
            match kind:
                case "pmst":
                    entries.extend(parse_pmst(path, root))
                case "strings":
                    entries.extend(parse_apple_strings(path, root))
                case "tw10428":
                    entries.extend(parse_tw10428(path, root, ui_lang))
                case "json":
                    entries.extend(parse_locale_json(path, root))
                case "properties":
                    entries.extend(parse_properties(path, root))
                case "zstring":
                    entries.extend(parse_zstring_file(path, root, ui_lang))
            stats[kind] += len(entries) - before
            stats[f"files:{kind}"] += 1
        except Exception as exc:  # noqa: BLE001
            stats["errors"] += 1
            logger.error("Failed {} ({}): {}", path, kind, exc)
    return entries, stats


# --------------------------------------------------------------------------- #
# TMX
# --------------------------------------------------------------------------- #


def build_tables(entries: list[Entry]) -> dict[str, dict[tuple[str, str], Entry]]:
    tables: dict[str, dict[tuple[str, str], Entry]] = defaultdict(dict)
    for e in entries:
        text = decode_caret(clean_text(e.text)).strip()
        key = clean_text(e.key).strip()
        if not text or not key:
            continue
        tables[e.lang].setdefault(
            (e.domain, key), Entry(e.domain, key, e.lang, text, e.origin)
        )
    return tables


def pivot_text(
    domain: str, key: str, pivot: dict[tuple[str, str], Entry]
) -> str | None:
    """English text for a key; Apple .strings often use the English text as key."""
    src = pivot.get((domain, key))
    if src:
        return src.text
    if domain.startswith("strings:") and " " in key:
        return key
    return None


def write_tmx(
    path: Path,
    lang: str,
    table: dict[tuple[str, str], Entry],
    pivot: dict[tuple[str, str], Entry],
    dedupe: bool,
    skip_identical: bool,
) -> tuple[int, int]:
    """Keep resource pairing policy; delegate XML and atomic publication to Localizzy."""
    paired = 0

    def records():
        nonlocal paired
        seen: set[tuple[str, str]] = set()
        for (domain, key), entry in sorted(table.items()):
            source = pivot_text(domain, key, pivot) if lang != PIVOT else None
            if skip_identical and source == entry.text:
                continue
            signature = (source or key, entry.text)
            if dedupe and signature in seen:
                continue
            seen.add(signature)
            segments = (
                ((PIVOT, source), (lang, entry.text))
                if source
                else ((lang, entry.text),)
            )
            paired += bool(source)
            yield TMXRecord(
                key, segments, (("x-domain", domain), ("x-origin", entry.origin))
            )

    written = write_records(
        path,
        records(),
        source_lang=PIVOT,
        creation_tool="adobe2tmx",
        origin_format="AdobeResources",
    )
    return written, paired


def run(
    input: str,
    output: str,
    ui_lang: str | None = None,
    dedupe: bool = True,
    skip_identical: bool = False,
    include_infoplist: bool = False,
    verbose: bool = False,
) -> dict:
    """Convert an Adobe app folder's localization resources into per-language TMX files.

    Args:
        input: App folder, e.g. "/Applications/Adobe Photoshop 2026".
        output: Folder that receives <lang>.tmx files (created if missing).
        ui_lang: Language of ZStrings inside binaries; auto-detected when omitted.
        dedupe: Collapse identical (source, target) pairs within a language.
        skip_identical: Drop units whose target equals the English source.
        include_infoplist: Also read InfoPlist.strings bundle metadata.
        verbose: Debug logging.
    """
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO")
    root = Path(input).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Input folder not found: {root}")
    out = Path(output).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    lang = norm_lang(str(ui_lang)) if ui_lang else detect_ui_lang(root)
    if lang is None:
        raise SystemExit(f"Unrecognised --ui_lang {ui_lang!r}")
    logger.info("Scanning {} (ZString language: {})", root, lang)
    entries, stats = extract(root, lang, include_infoplist)
    logger.info("Extracted {} raw entries: {}", len(entries), dict(stats))
    if stats["errors"]:
        raise SystemExit(
            "Extraction has resource errors; existing outputs were preserved"
        )
    tables = build_tables(entries)
    pivot = tables.get(PIVOT, {})
    languages = []
    for tmx_lang in sorted(tables):
        target = out / f"{tmx_lang}.tmx"
        written, paired = write_tmx(
            target, tmx_lang, tables[tmx_lang], pivot, dedupe, skip_identical
        )
        languages.append(
            {
                "language": tmx_lang,
                "units": written,
                "paired": paired,
                "file": str(target),
            }
        )
    if not tables:
        logger.warning("No localization strings found under {}", root)
    return {
        "tool": "adobe2tmx",
        "input": str(root),
        "zstring_language": lang,
        "languages": languages,
        "stats": dict(stats),
    }
