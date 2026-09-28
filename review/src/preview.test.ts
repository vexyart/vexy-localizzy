// this_file: review/src/preview.test.ts
// @vitest-environment jsdom
import { expect, test } from "vitest";
import { renderPreview } from "./renderPreview";
import type { Unit } from "./types";
const xml = `<ui><class>Dialog</class><widget class="QDialog" name="Dialog"><widget class="QPushButton" name="open"><property name="text"><string>Open</string></property></widget></widget></ui>`;
const unit: Unit = { key: "open", context: "Dialog", source: "Open", disambiguation: null, slots: { scalar: "Otwórz" }, source_plural: null, target: "Otwórz", notes: [], locations: [], state: "needs_review", editable: true, max_length: null };
test("published renderer translates and maps a clicked string to its message", () => {
  const doc = document.implementation.createHTMLDocument(); const clicked: string[] = [];
  renderPreview(doc, xml, [unit], unit.key, { scalar: "Otwórz plik" }, true, key => clicked.push(key));
  const button = doc.querySelector('.QPushButton[data-quiht-key="open.text"]') as HTMLElement;
  expect(button.textContent).toBe("Otwórz plik"); button.click(); expect(clicked).toEqual(["open"]);
});
test("ambiguous context never silently selects a different message", () => {
  const doc = document.implementation.createHTMLDocument();
  renderPreview(doc, xml, [unit, { ...unit, key: "second" }], "", {}, true, () => { throw Error("Ambiguous selection"); });
  expect(doc.querySelector('.QPushButton[data-quiht-key="open.text"]')?.textContent).toBe("Open");
});
test("submitted markup is displayed as text without executable content", () => {
  const doc = document.implementation.createHTMLDocument();
  renderPreview(doc, xml, [unit], unit.key, { scalar: `<img src=x onerror="alert(1)"><script>alert(2)</script>` }, true, () => {});
  expect(doc.querySelectorAll("script,[onerror],iframe")).toHaveLength(0);
  expect(doc.querySelector('.QPushButton[data-quiht-key="open.text"]')?.textContent).toContain("<script>");
});
test("native line edit text is rendered and notr strings stay untranslated", () => {
  const doc = document.implementation.createHTMLDocument();
  const source = `<ui><class>Dialog</class><widget class="QDialog" name="Dialog"><widget class="QLineEdit" name="name"><property name="text"><string>Open</string></property></widget><widget class="QPushButton" name="constant"><property name="text"><string notr="true">Open</string></property></widget></widget></ui>`;
  renderPreview(doc, source, [unit], unit.key, { scalar: "Otwórz" }, true, () => {});
  expect((doc.querySelector("input") as HTMLInputElement).value).toBe("Otwórz");
  expect(doc.querySelector('[data-q-name="constant"]')?.textContent).toBe("Open");
  expect(doc.querySelector('[data-q-name="constant"]')?.hasAttribute("data-review-key")).toBe(false);
});
