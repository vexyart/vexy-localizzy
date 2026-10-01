# this_file: src/vexy_localizzy/memory/tmx_html.py
"""Render a two-language TMX as one self-contained, filterable HTML page.

The page embeds the units as JSON and builds the table in the browser: one
row per unit with source, target, the unit's ``x-*`` properties and notes.
Every property with a small set of values becomes a filter; clicking a source
or target copies it to the clipboard. The TMX is streamed, so large memories
render without loading the XML tree, and the page is written atomically.
"""

import json
import os
import tempfile
from collections import Counter
from html import escape
from pathlib import Path

from loguru import logger

from vexy_localizzy.locales import canonical_locale
from vexy_localizzy.memory.tmx_read import Unit, read_tmx

MAX_FILTER_VALUES = 40  # a property with more distinct values is shown, not filtered

PAGE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root { --bg:#fff; --fg:#111; --muted:#666; --line:#ddd; --hl:#eee; --tag:#e8eefc; }
@media (prefers-color-scheme:dark) { :root { --bg:#151515; --fg:#eee; --muted:#999; --line:#333; --hl:#2a2a2a; --tag:#25304a; } }
body { margin:0; font:12px/1.35 system-ui,sans-serif; background:var(--bg); color:var(--muted); }
#bar { position:sticky; top:0; z-index:2; display:flex; flex-wrap:wrap; align-items:center; gap:6px 8px; padding:6px 12px; background:var(--bg); border-bottom:1px solid var(--line); }
#bar h1 { margin:0 4px 0 0; font-size:12px; font-weight:600; color:var(--fg); }
#bar h1 small { font-weight:400; color:var(--muted); }
#bar input,#bar select,#bar button { height:26px; font:inherit; font-size:12px; color:var(--fg); background:var(--bg); border:1px solid var(--line); border-radius:4px; padding:0 6px; }
#search { flex:1 1 180px; min-width:120px; }
#stats { flex:1 1 auto; font-size:11px; font-variant-numeric:tabular-nums; white-space:nowrap; }
main { padding:0 12px 12px; }
table { width:100%; table-layout:fixed; border-collapse:collapse; }
th { position:sticky; top:var(--bar,39px); z-index:1; padding:3px 8px; text-align:left; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.05em; background:var(--bg); border-bottom:1px solid var(--line); }
th.src,th.tgt { width:30%; } th.props { width:16%; }
td { padding:4px 8px; vertical-align:top; white-space:pre-wrap; overflow-wrap:anywhere; border-bottom:1px solid var(--line); }
.text { font-size:14px; line-height:1.3; color:var(--fg); cursor:copy; border-radius:3px; } .text:hover { background:var(--hl); }
td.src .text { font-weight:600; }
.prop { display:inline-block; margin:0 4px 2px 0; padding:0 4px; border-radius:3px; background:var(--tag); color:var(--fg); font-size:10px; white-space:nowrap; }
.prop b { font-weight:600; opacity:.7; }
.prop.long { display:block; white-space:pre-wrap; background:none; padding:0; font-size:10px; color:var(--muted); }
.note { font-size:11px; line-height:1.4; } .note+.note { margin-top:3px; }
#empty,footer { padding:10px 8px; font-size:11px; }
#toast { position:fixed; left:50%; bottom:18px; transform:translateX(-50%); padding:6px 12px; border-radius:6px; background:var(--fg); color:var(--bg); font-size:12px; opacity:0; transition:opacity .2s; pointer-events:none; max-width:80vw; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
#toast.show { opacity:.95; }
</style>
<div id="bar">
  <h1>__TITLE__ <small>__SUBTITLE__</small></h1>
  <input id="search" type="search" placeholder="Filter source, target, notes…" aria-label="Filter">
  <span id="filters"></span>
  <select id="sort" aria-label="Sort"><option value="file">File order</option><option value="source">Source A–Z</option><option value="target">Target A–Z</option></select>
  <span id="stats" role="status" aria-live="polite"></span>
  <button id="notes" aria-pressed="true">Notes</button>
  <button id="reset">Reset</button>
</div>
<main>
  <table><thead><tr><th class="src">__SRC__</th><th class="tgt">__TGT__</th><th class="props">Properties</th><th>Notes</th></tr></thead><tbody id="rows"></tbody></table>
  <p id="empty" hidden>No units match these filters.</p>
  <footer>Click a source or target to copy it. Properties are the unit's <code>x-*</code> values; those with few distinct values are offered as filters.</footer>
</main>
<div id="toast" role="status" aria-live="polite"></div>
<script type="application/json" id="data">__DATA__</script>
<script>
'use strict';
const payload=JSON.parse(document.getElementById('data').textContent), units=payload.units;
const $=id=>document.getElementById(id);
function element(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
const selects={};
for(const [prop,values] of Object.entries(payload.filters)){
  const s=element('select');s.setAttribute('aria-label',prop);const all=element('option','All '+prop.replace(/^x-/,''));all.value='';s.append(all);
  for(const v of values){const o=element('option',v);o.value=v;s.append(o);}
  s.addEventListener('input',render);$('filters').append(s);selects[prop]=s;
}
let showNotes=true;
function render(){
  const q=$('search').value.toLocaleLowerCase();
  let rows=units.filter(u=>{
    for(const [p,s] of Object.entries(selects))if(s.value&&(u.props[p]||'')!==s.value)return false;
    if(!q)return true;
    const hay=[u.source,u.target,u.tuid,...u.notes,...Object.values(u.props)];
    return hay.some(x=>x.toLocaleLowerCase().includes(q));
  });
  const s=$('sort').value;
  if(s==='source')rows=rows.slice().sort((a,b)=>a.source.localeCompare(b.source));
  if(s==='target')rows=rows.slice().sort((a,b)=>a.target.localeCompare(b.target));
  $('stats').textContent=`${rows.length.toLocaleString()} of ${units.length.toLocaleString()} units`;
  const body=document.createDocumentFragment();
  for(const u of rows){
    const tr=element('tr'), src=element('td',undefined,'src'), tgt=element('td',undefined,'tgt'), props=element('td'), notes=element('td');
    src.append(element('span',u.source,'text'));tgt.append(element('span',u.target,'text'));
    for(const [k,v] of Object.entries(u.props)){const p=element('span',undefined,v.length>60?'prop long':'prop');p.append(element('b',k.replace(/^x-/,'')+' '),document.createTextNode(v));props.append(p);}
    if(showNotes)for(const n of u.notes)notes.append(element('div',n,'note'));
    tr.append(src,tgt,props,notes);body.append(tr);
  }
  $('rows').replaceChildren(body);$('empty').hidden=rows.length>0;
}
let toastTimer;
function toast(msg){const t=$('toast');t.textContent=msg;t.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('show'),1400);}
function copyText(text){
  // execCommand runs synchronously inside the click gesture; the async clipboard API is the fallback.
  let done=false;
  const ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.opacity='0';document.body.append(ta);ta.select();
  try{done=document.execCommand('copy');}catch(e){done=false;}finally{ta.remove();}
  if(!done&&navigator.clipboard)navigator.clipboard.writeText(text).catch(()=>{});
  toast('Copied “'+text+'”');
}
function measure(){document.documentElement.style.setProperty('--bar',$('bar').offsetHeight+'px');}
$('search').addEventListener('input',render);$('sort').addEventListener('input',render);
$('rows').addEventListener('click',e=>{const c=e.target.closest('.text');if(c)copyText(c.textContent);});
$('notes').onclick=()=>{showNotes=!showNotes;$('notes').setAttribute('aria-pressed',String(showNotes));render();};
$('reset').onclick=()=>{$('search').value='';$('sort').value='file';for(const s of Object.values(selects))s.value='';render();};
addEventListener('resize',measure);addEventListener('load',measure);render();measure();
</script>
</html>
"""


def _row(unit: Unit, source: str, target: str) -> dict | None:
    """One JSON row, or None when the unit lacks either language."""
    picked = {}
    for segment in unit.segments:
        if segment.language in (source, target) and segment.language not in picked:
            picked[segment.language] = segment
    if source not in picked or target not in picked:
        return None
    src, tgt = picked[source], picked[target]
    return {
        "tuid": unit.tuid,
        "source": src.text,
        "target": tgt.text,
        "props": {k: v for k, v in unit.properties if k.startswith("x-")},
        "notes": [*unit.notes, *src.notes, *tgt.notes],
    }


def _detect_target(path: Path, source: str) -> str:
    """The one non-source language in the file; ambiguity is an error."""
    seen: set[str] = set()
    for unit in read_tmx(path):
        seen.update(s.language for s in unit.segments if s.language != source)
        if len(seen) > 1:
            break
    if len(seen) != 1:
        raise ValueError(
            f"Pass --target: found {sorted(seen) or 'no'} target languages besides {source}"
        )
    return seen.pop()


def tmx2html(
    input: str,
    output: str,
    target: str | None = None,
    src_lang: str = "en",
    title: str | None = None,
    verbose: bool = False,
) -> dict:
    """Render a TMX as a self-contained HTML table with filters and click-to-copy.

    Args:
        input: source TMX (or .tmx.gz) file.
        output: destination .html file, atomically replaced.
        target: target language tag; detected when the file has exactly one.
        src_lang: source language tag (default en).
        title: page heading; defaults to the input file name.
        verbose: log the counts.

    Units missing either language are skipped and counted, not invented.
    """
    source_path, output_path = Path(input), Path(output)
    if source_path.resolve() == output_path.resolve():
        raise ValueError("Input and output must be different files")
    source = canonical_locale(src_lang)
    target = canonical_locale(target) if target else _detect_target(source_path, source)
    rows, skipped = [], 0
    for unit in read_tmx(source_path):
        row = _row(unit, source, target)
        if row is None:
            skipped += 1
        else:
            rows.append(row)
    if not rows:
        raise ValueError(f"No {source}→{target} units to render")
    values: dict[str, Counter] = {}
    for row in rows:
        for k, v in row["props"].items():
            values.setdefault(k, Counter())[v] += 1
    filters = {
        k: sorted(c) for k, c in sorted(values.items()) if len(c) <= MAX_FILTER_VALUES
    }
    heading = title or source_path.name
    payload = {"source": source, "target": target, "filters": filters, "units": rows}
    page = (
        PAGE.replace("__TITLE__", escape(heading))
        .replace("__SUBTITLE__", escape(f"{source} → {target}"))
        .replace("__SRC__", escape(source))
        .replace("__TGT__", escape(target))
        .replace(
            "__DATA__", json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(page)
        # NamedTemporaryFile creates 0600; a page is meant to be served or shared.
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(temporary, 0o666 & ~umask)
        os.replace(temporary, output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if verbose:
        logger.info(
            "{}: {} units, {} skipped → {}",
            source_path,
            len(rows),
            skipped,
            output_path,
        )
    return {
        "output": str(output_path),
        "source": source,
        "target": target,
        "units": len(rows),
        "skipped": skipped,
        "filters": list(filters),
    }
