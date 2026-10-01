# this_file: tests/memory/test_tmx_html.py
"""HTML rendering embeds every unit, offers property filters and copies on click."""

import json
import os
import re
from pathlib import Path

import pytest

from vexy_localizzy.cli.tm import TM_COMMANDS
from vexy_localizzy.memory.tmx_html import tmx2html


def memory(tmp_path: Path, units: str) -> Path:
    path = tmp_path / "input.tmx"
    path.write_text(
        f'<tmx version="1.4"><header srclang="en"/><body>{units}</body></tmx>',
        encoding="utf-8",
    )
    return path


UNITS = """
<tu tuid="term:stem"><prop type="x-status">approved</prop><prop type="x-category">type-design</prop><prop type="x-fallback">main stroke</prop>
  <note>Definition &lt;b&gt;.</note>
  <tuv xml:lang="en"><seg>stem</seg></tuv>
  <tuv xml:lang="pl"><note>Founder decision.</note><seg>trzon</seg></tuv></tu>
<tu tuid="term:brand"><prop type="x-status">do-not-translate</prop><prop type="x-category">brand</prop>
  <tuv xml:lang="en"><seg>DemoApp</seg></tuv><tuv xml:lang="pl"><seg>DemoApp</seg></tuv></tu>
<tu tuid="term:tricky"><tuv xml:lang="en"><seg>a &lt;/script&gt;&lt;!--&lt;script&gt; b</seg></tuv>
  <tuv xml:lang="pl"><seg>c</seg></tuv></tu>
<tu><tuv xml:lang="en"><seg>orphan</seg></tuv></tu>
"""


def embedded(page: str) -> dict:
    match = re.search(
        r'<script type="application/json" id="data">(.*?)</script>', page, re.S
    )
    assert match, "page embeds its data"
    return json.loads(match.group(1))


def test_render_embeds_units_filters_and_copy_handler(tmp_path):
    source = memory(tmp_path, UNITS)
    out = tmp_path / "nested" / "pl.html"
    result = TM_COMMANDS["tmx2html"](str(source), str(out), title="Polish terms")
    assert result == {
        "output": str(out),
        "source": "en",
        "target": "pl",
        "units": 3,
        "skipped": 1,
        "filters": ["x-category", "x-fallback", "x-status"],
    }, "target detected, orphan unit skipped, small-valued props become filters"
    page = out.read_text(encoding="utf-8")
    assert "<title>Polish terms</title>" in page
    assert page.count("</script>") == 2, (
        "embedded data cannot close the script element early"
    )
    data = embedded(page)
    assert data["units"][2]["source"] == "a </script><!--<script> b", (
        "round trip through the escape"
    )
    assert data["filters"]["x-status"] == ["approved", "do-not-translate"]
    stem = data["units"][0]
    assert stem == {
        "tuid": "term:stem",
        "source": "stem",
        "target": "trzon",
        "props": {
            "x-status": "approved",
            "x-category": "type-design",
            "x-fallback": "main stroke",
        },
        "notes": ["Definition <b>.", "Founder decision."],
    }
    umask = os.umask(0)
    os.umask(umask)
    assert (out.stat().st_mode & 0o777) == (0o666 & ~umask), (
        "page gets the umask mode, not a 0600 temp file"
    )
    first = out.read_bytes()
    tmx2html(str(source), str(out), title="Polish terms")
    assert out.read_bytes() == first, "rendering is deterministic"


def test_explicit_target_and_errors(tmp_path):
    source = memory(
        tmp_path,
        '<tu><tuv xml:lang="en"><seg>A</seg></tuv><tuv xml:lang="de"><seg>B</seg></tuv>'
        '<tuv xml:lang="fr"><seg>C</seg></tuv></tu>',
    )
    out = tmp_path / "out.html"
    with pytest.raises(ValueError, match="Pass --target"):
        tmx2html(str(source), str(out))
    assert tmx2html(str(source), str(out), target="fr")["units"] == 1
    with pytest.raises(ValueError, match="No en→es units"):
        tmx2html(str(source), str(tmp_path / "other.html"), target="es")
    assert not (tmp_path / "other.html").exists(), "a failed render writes nothing"
    with pytest.raises(ValueError, match="different files"):
        tmx2html(str(source), str(source))
