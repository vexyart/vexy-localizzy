// this_file: review/src/useQuality.ts
import { useEffect, useState } from "react";
import { api, catalogPath } from "./api";
import type { Finding, Quality, Suggestion, Unit } from "./types";
export function useQuality(id: string, revision: string, unit: Unit | undefined, targets: Record<string, string>) {
  const [quality, setQuality] = useState<Quality>({ checking: false, error: "", findings: [] });
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [suggestionError, setSuggestionError] = useState("");
  useEffect(() => {
    if (!unit?.editable) { setQuality({ checking: false, error: "", findings: [] }); return; }
    const controller = new AbortController(); setQuality({ checking: true, error: "", findings: [] });
    const timer = setTimeout(() => {
      api<{ findings: Finding[] }>(catalogPath(id) + "/validate", { method: "POST", signal: controller.signal, body: JSON.stringify({ key: unit.key, revision, targets, action: "draft" }) })
        .then(value => setQuality({ checking: false, error: "", findings: value.findings }))
        .catch(error => { if (!controller.signal.aborted) setQuality({ checking: false, error: error.message, findings: [] }); });
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [id, revision, unit, targets]);
  useEffect(() => {
    setSuggestions([]); setSuggestionError(""); if (!unit) return;
    const controller = new AbortController();
    api<Suggestion[]>(catalogPath(id) + "/suggestions?key=" + encodeURIComponent(unit.key), { signal: controller.signal }).then(setSuggestions).catch(error => { if (!controller.signal.aborted) setSuggestionError(error.message); });
    return () => controller.abort();
  }, [id, unit]);
  return { quality, suggestions, suggestionError };
}
