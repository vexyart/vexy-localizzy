// this_file: review/src/renderPreview.ts
import DOMPurify from "dompurify";
import { parse, render } from "quiht-core";
import quihtCss from "quiht-core/index.css?inline";
import type { Unit } from "./types";
import { populatePreviewInputs } from "./previewText";

export function renderPreview(doc: Document, xml: string, units: Unit[], selected: string, targets: Record<string, string>, localized: boolean, onSelect: (key: string) => void, scale = "fit") {
  const parsed = parse(xml);
  const context = parsed.querySelector("ui > class")?.textContent ?? "";
  const comments = new Map<string, string | null>();
  const constants = new Set<string>();
  for (const text of parsed.querySelectorAll("string")) {
    const property = text.closest("property,attribute");
    const widget = property?.parentElement?.closest("widget,action");
    if (property && widget) {
      const key = `${widget.getAttribute("name")}.${property.getAttribute("name")}`;
      comments.set(key, text.getAttribute("comment"));
      if (["true", "yes"].includes(text.getAttribute("notr") ?? "")) constants.add(key);
    }
  }
  const match = (key: string, original: string) => {
    if (constants.has(key)) return undefined;
    const candidates = units.filter(unit => unit.context === context && unit.source === original && (unit.disambiguation || null) === (comments.get(key) || null));
    return candidates.length === 1 ? candidates[0] : undefined;
  };
  doc.body.replaceChildren();
  doc.head.querySelectorAll("style").forEach(node => node.remove());
  const style = doc.createElement("style");
  style.textContent = quihtCss + `
    html,body{margin:0;width:100%;height:100%;background:#edf2f5;font:16px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    :root{--q-font-size:16px;--q-text-color:#101b30;--q-window-bg:#fff;--q-border-color:#c9d2de;--q-primary-color:#008899}
    body{display:flex;align-items:safe center;justify-content:safe center;box-sizing:border-box;padding:32px 32px 124px;overflow:auto}
    body>.QWidget{flex-shrink:0}
    body>.QDialog{box-shadow:0 8px 22px #142c4426;border-radius:8px}
    .q-dialog-titlebar{height:40px;flex-shrink:0;box-sizing:border-box;background:#f3f4f6;font-weight:400;padding:8px 16px;border-color:#e1e6ec}
    .q-dialog-titlebar .QPushButton{border:0;background:none;font-size:24px}
    .QPushButton{background:#f7f8fa;border-radius:6px}
    .QLineEdit{border-radius:6px;padding:0 12px}
    .quiht-translatable-node{outline:none}
    .quiht-translatable-node[data-review-key]{cursor:pointer}
    [data-review-selected]{outline:1px solid #008899;outline-offset:0;background:#e3f3f5}
    @media(max-width:450px){body{padding:20px;align-items:flex-start;justify-content:flex-start}}
  `;
  doc.head.append(style);
  const translate = (key: string, original: string) => {
    const unit = match(key, original);
    if (!localized || !unit) return original;
    return Object.values(unit.key === selected ? targets : unit.slots)[0] || original;
  };
  const root = render(parsed, {
    targetDocument: doc,
    resourceResolver: { resolveResource: () => "" },
    translationResolver: { translate },
  });
  populatePreviewInputs(root, parsed, translate);
  root.style.position = "relative"; root.style.left = "auto"; root.style.top = "auto";
  DOMPurify.sanitize(root, { IN_PLACE: true, FORBID_TAGS: ["script", "iframe", "object", "embed", "link", "form"], FORBID_ATTR: ["srcdoc"] });
  for (const element of root.querySelectorAll<HTMLElement>("[data-quiht-key]")) {
    const unit = match(element.dataset.quihtKey ?? "", element.dataset.quihtOriginal ?? "");
    if (!unit) continue;
    element.dataset.reviewKey = unit.key;
    element.dir = "auto";
    if (unit.key === selected) element.dataset.reviewSelected = "true";
  }
  root.addEventListener("click", event => {
    event.preventDefault();
    const element = (event.target as Element).closest<HTMLElement>("[data-review-key]");
    if (element?.dataset.reviewKey) onSelect(element.dataset.reviewKey);
  });
  doc.body.append(root);
  const resize = () => {
    if (!root.offsetWidth || !root.offsetHeight) return;
    const padding = doc.documentElement.clientWidth <= 450 ? 40 : 64;
    const vertical = doc.documentElement.clientWidth <= 450 ? 40 : 156;
    root.style.zoom = scale === "fit" ? String(Math.max(.1, Math.min(1, (doc.documentElement.clientWidth - padding) / root.offsetWidth, (doc.documentElement.clientHeight - vertical) / root.offsetHeight))) : scale;
  };
  resize();
  const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
  observer?.observe(doc.documentElement);
  return () => observer?.disconnect();
}
