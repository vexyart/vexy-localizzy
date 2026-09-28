// this_file: review/src/App.tsx
import { useState } from "react";
import { catalogPath } from "./api";
import { DiscardDialog } from "./DiscardDialog";
import { Editor } from "./Editor";
import { Messages } from "./Messages";
import { Preview } from "./Preview";
import { language } from "./types";
import { useReview } from "./useReview";

export function App() {
  const work = useReview();
  const [exportError, setExportError] = useState("");
  const [exporting, setExporting] = useState(false);
  async function exportTS() {
    setExportError("");
    if (work.dirty) { setExportError("Save your changes before exporting the TS catalog."); return; }
    setExporting(true);
    try {
      const response = await fetch(catalogPath(work.catalogId) + "/export.ts", { signal: AbortSignal.timeout(20000) });
      if (!response.ok) throw Error("Could not export the catalog. Try again.");
      if (response.headers.get("ETag") !== `"${work.catalog?.revision}"`) throw Error("Catalog changed. Reload the saved version before exporting.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url; link.download = "reviewed.ts"; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { setExportError(error instanceof Error ? error.message : "Export failed."); }
    finally { setExporting(false); }
  }
  const error = work.error || exportError;
  return <div className="app-shell">
    <header className="app-toolbar"><span className="wordmark">Localizzy</span><h1>Translation review</h1>
      <select aria-label="Catalog" value={work.catalogId} disabled={work.busy || work.loading} onChange={event => { setExportError(""); work.switchCatalog(event.target.value); }}>
        {work.catalogs.map(item => <option key={item.id} value={item.id}>{item.id.charAt(0).toUpperCase() + item.id.slice(1)} · {language(item.target_lang)}</option>)}
      </select>
      <button className="primary export-button" disabled={!work.catalog || work.busy || work.loading || exporting} onClick={() => void exportTS()}>{exporting ? "Exporting…" : "Export TS"}</button>
    </header>
    {error && <div className="error-banner" role="alert"><span>{error}</span><button onClick={() => { setExportError(""); if (work.catalogId) work.reopen(); else window.location.reload(); }}>Reload saved version</button>{exportError && <button onClick={() => setExportError("")}>Dismiss</button>}</div>}
    {work.loading ? <p className="empty" role="status">Loading catalogs…</p> : work.catalog ? <main className="workspace">
      <Messages catalog={work.catalog} filtered={work.filtered} selected={work.selected} query={work.query} unreviewed={work.unreviewed} busy={work.busy} onQuery={work.setQuery} onFilter={work.setUnreviewed} onSelect={work.select} onMove={work.move}/>
      <Preview assets={work.assets} units={work.catalog.units} selected={work.selected} targets={work.targets} onSelect={work.select}/>
      <Editor catalog={work.catalog} unit={work.unit} targets={work.targets} onTargets={value => { setExportError(""); work.setTargets(value); }} reason={work.reason} onReason={work.setReason} dirty={work.dirty} busy={work.busy} onSave={(action, next) => { setExportError(""); void work.save(action, next); }} onReopen={work.reopen}/>
    </main> : !error && <p className="empty">No catalogs configured.</p>}
    {work.pending && <DiscardDialog onKeep={() => work.setPending(null)} onDiscard={() => { if (work.pending) work.applySwitch(work.pending); }}/>} 
  </div>;
}
