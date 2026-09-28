// this_file: review/src/Preview.tsx
import { useEffect, useRef, useState } from "react";
import { renderPreview } from "./renderPreview";
import type { Asset, Unit } from "./types";

const FRAME = `<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'"></head><body></body></html>`;

type Props = { assets: Asset[]; units: Unit[]; selected: string; targets: Record<string, string>; onSelect: (key: string) => void };
export function Preview({ assets, units, selected, targets, onSelect }: Props) {
  const [asset, setAsset] = useState(""); const [xml, setXml] = useState("");
  const [localized, setLocalized] = useState(true); const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(""); const frame = useRef<HTMLIFrameElement>(null);
  const [scale, setScale] = useState("fit");
  useEffect(() => { if (!asset && assets.length) setAsset(assets[0].id); }, [asset, assets]);
  useEffect(() => {
    if (!asset) return;
    const controller = new AbortController(); setError(""); setXml("");
    fetch(`/api/ui/${encodeURIComponent(asset)}`, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]) })
      .then(response => { if (!response.ok) throw Error("Could not load UI preview."); return response.text(); })
      .then(setXml).catch(error => { if (!controller.signal.aborted) setError(String(error.message)); });
    return () => controller.abort();
  }, [asset]);
  useEffect(() => {
    if (!loaded || !xml || !frame.current?.contentDocument) return;
    try { const dispose = renderPreview(frame.current.contentDocument, xml, units, selected, targets, localized, onSelect, scale); setError(""); return dispose; }
    catch (error) { setError(error instanceof Error ? error.message : "Preview unavailable"); }
  }, [loaded, xml, units, selected, targets, localized, onSelect, scale]);
  return <section className="preview-panel" aria-label="UI preview">
    <div className="preview-heading"><h2>UI preview</h2><select aria-label="UI asset" value={asset} onChange={event => setAsset(event.target.value)} disabled={!assets.length}>{assets.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
    <div className="preview-tabs" role="tablist" aria-label="Preview language"><button role="tab" aria-selected={!localized} onClick={() => setLocalized(false)}>Original</button><button role="tab" aria-selected={localized} onClick={() => setLocalized(true)}>Localized</button></div>
    <div className="preview-canvas">{error && <p className="error" role="alert">{error}</p>}{!assets.length && <p className="empty">No UI file configured. All messages remain editable.</p>}<iframe ref={frame} title="Rendered application UI" sandbox="allow-same-origin" srcDoc={FRAME} onLoad={() => setLoaded(true)} hidden={!xml || !!error} /></div>
    <div className="preview-hint"><span>Preview updates as you type.</span><select aria-label="Preview scale" value={scale} onChange={event => setScale(event.target.value)}><option value="fit">Fit</option><option value="1">100%</option><option value="0.75">75%</option><option value="0.5">50%</option></select></div>
  </section>;
}
