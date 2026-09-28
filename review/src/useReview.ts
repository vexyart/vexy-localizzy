// this_file: review/src/useReview.ts
import { useEffect, useMemo, useRef, useState } from "react";
import { api, catalogPath } from "./api";
import type { Asset, Catalog, Summary } from "./types";

type Switch = { kind: "unit"; value: string } | { kind: "catalog"; value: string } | { kind: "reload"; value: string };
export function useReview() {
  const [catalogs, setCatalogs] = useState<Summary[]>([]); const [assets, setAssets] = useState<Asset[]>([]);
  const [catalogId, setCatalogId] = useState(""); const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [selected, setSelected] = useState(""); const [targets, setTargets] = useState<Record<string, string>>({});
  const [reason, setReason] = useState(""); const [query, setQuery] = useState(""); const [unreviewed, setUnreviewed] = useState(false);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<Switch | null>(null); const [reload, setReload] = useState(0); const selectedRef = useRef("");
  const unit = catalog?.units.find(item => item.key === selected);
  const dirty = !!unit && (JSON.stringify(targets) !== JSON.stringify(unit.slots) || !!reason.trim());
  const filtered = useMemo(() => (catalog?.units ?? []).filter(item => (!unreviewed || (item.editable && item.state !== "approved")) && `${item.source} ${Object.values(item.slots).join(" ")} ${item.context}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())), [catalog, query, unreviewed]);
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([api<Summary[]>("/api/catalogs", { signal: controller.signal }), api<Asset[]>("/api/ui", { signal: controller.signal })])
      .then(([catalogs, assets]) => { setCatalogs(catalogs); setAssets(assets); setCatalogId(catalogs[0]?.id ?? ""); if (!catalogs.length) setLoading(false); })
      .catch(error => { if (!controller.signal.aborted) { setError(error.message); setLoading(false); } });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!catalogId) return;
    const controller = new AbortController(); setLoading(true); setError(""); setCatalog(null);
    api<Catalog>(catalogPath(catalogId), { signal: controller.signal }).then(value => {
      setCatalog(value); const key = value.units.some(item => item.key === selectedRef.current) ? selectedRef.current : value.units[0]?.key ?? "";
      selectedRef.current = key; setSelected(key); setTargets({ ...value.units.find(item => item.key === key)?.slots }); setReason(""); setLoading(false);
    }).catch(error => { if (!controller.signal.aborted) { setError(error.message); setLoading(false); } });
    return () => controller.abort();
  }, [catalogId, reload]);
  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => { if (dirty) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", guard); return () => window.removeEventListener("beforeunload", guard);
  }, [dirty]);
  function applySwitch(next: Switch) {
    setError(""); setPending(null); setReason("");
    if (next.kind === "catalog") { setCatalogId(next.value); return; }
    if (next.kind === "reload") { setReload(value => value + 1); return; }
    selectedRef.current = next.value; setSelected(next.value); setTargets({ ...catalog?.units.find(item => item.key === next.value)?.slots });
  }
  function requestSwitch(next: Switch) { if (busy || loading) return; if (dirty) setPending(next); else applySwitch(next); }
  const select = (key: string) => { if (key !== selected) requestSwitch({ kind: "unit", value: key }); };
  function move(delta: number) { const next = filtered[filtered.findIndex(item => item.key === selected) + delta]; if (next) select(next.key); }
  async function save(action: "draft" | "approve", advance = false) {
    if (!catalog || !unit?.editable || busy || loading) return;
    setBusy(true); setError("");
    const next = advance ? filtered[filtered.findIndex(item => item.key === selected) + 1]?.key : undefined;
    try {
      const value = await api<Catalog>(catalogPath(catalogId) + "/edits", { method: "POST", body: JSON.stringify({ key: selected, revision: catalog.revision, targets, action, reason }) });
      setCatalog(value); setCatalogs(items => items.map(item => item.id === value.id ? value : item));
      const key = next ?? selected; selectedRef.current = key; setSelected(key); setTargets({ ...value.units.find(item => item.key === key)?.slots }); setReason("");
    } catch (error) { setError(error instanceof Error ? error.message : "Save failed. Your draft is still here."); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (pending || busy || loading) return;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") { event.preventDefault(); void save("draft"); }
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); void save("approve", true); }
      if (event.altKey && ["ArrowUp", "ArrowDown"].includes(event.key)) { event.preventDefault(); move(event.key === "ArrowUp" ? -1 : 1); }
    };
    window.addEventListener("keydown", handler); return () => window.removeEventListener("keydown", handler);
  });
  return { catalogs, assets, catalogId, catalog, selected, targets, setTargets, reason, setReason, query, setQuery, unreviewed, setUnreviewed, error, busy, loading, pending, setPending, unit, dirty, filtered, select, move, save, applySwitch, switchCatalog: (value: string) => requestSwitch({ kind: "catalog", value }), reopen: () => requestSwitch({ kind: "reload", value: "" }) };
}
