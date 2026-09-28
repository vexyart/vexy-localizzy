// this_file: review/src/previewText.ts
// quiht-core 1.0.8 renders placeholders but omits QLineEdit.text and plainText.
export function populatePreviewInputs(root: HTMLElement, parsed: Document, translate: (key: string, original: string) => string) {
  for (const node of parsed.querySelectorAll('widget[class="QLineEdit"], widget[class="QPlainTextEdit"]')) {
    const name = node.getAttribute("name");
    const property = node.getAttribute("class") === "QLineEdit" ? "text" : "plainText";
    const text = node.querySelector(`:scope > property[name="${property}"] > string`);
    const element = Array.from(root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input,textarea")).find(item => item.dataset.qName === name);
    if (!text || !element) continue;
    const key = `${name}.${property}`; const original = text.textContent ?? "";
    element.value = translate(key, original); element.readOnly = true; element.dir = "auto";
    element.dataset.quihtKey = key; element.dataset.quihtOriginal = original;
    element.classList.add("quiht-translatable-node");
  }
}
