// @vitest-environment jsdom
// this_file: review/src/App.test.tsx
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
// jsdom lacks native modal behavior; browser QA checks focus trapping and Escape.
beforeEach(() => { HTMLDialogElement.prototype.showModal = function () { this.open = true; }; });

function setup({ unchanged = false, holdSave = false, targetLang = "pl" } = {}) {
  let release = () => {};
  const pendingSave = new Promise<void>(resolve => { release = resolve; });
  let catalog = { id: "sample", source_lang: "en", target_lang: targetLang, total: 2, approved: 0, revision: "a".repeat(64), units: ["Open file", "Cancel"].map((source, i) => ({ key: String(i), context: "FileDialog", source, source_plural: null, target: "", disambiguation: null, notes: [], locations: [], state: "needs_review", slots: { scalar: i ? "Anuluj" : "Otwórz" }, editable: true, max_length: null })) };
  const fetch = vi.fn(async (path: string, options?: RequestInit) => {
    if (path.endsWith("/edits")) {
      if (holdSave) await pendingSave;
      const edit = JSON.parse(String(options?.body));
      catalog = { ...catalog, revision: "b".repeat(64), units: catalog.units.map(unit => unit.key === edit.key ? { ...unit, slots: edit.targets } : unit) };
    }
    const body = path === "/api/catalogs" ? [catalog] : path === "/api/ui" || path.includes("/suggestions?") ? [] : path.endsWith("/validate") ? { findings: unchanged ? [{rule_id: "TARGET-UNCHANGED", message: "Unchanged text", severity: "minor"}] : [] } : catalog;
    return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetch);
  render(<App/>);
  return { fetch, release };
}

test("draft remains when navigation is cancelled and save sends its revision", async () => {
  const { fetch } = setup();
  const input = await screen.findByRole("textbox", { name: "Translation · Polish" });
  fireEvent.change(input, { target: { value: "Otwórz plik" } });
  fireEvent.click(screen.getByRole("button", { name: /^Cancel, FileDialog/ }));
  expect(screen.getByRole("alertdialog")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));
  expect((input as HTMLTextAreaElement).value).toBe("Otwórz plik");
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await waitFor(() => expect(screen.getByRole("status").textContent).toBe("Saved"));
  const write = fetch.mock.calls.find(([path]) => path.endsWith("/edits"));
  expect(JSON.parse(String(write?.[1]?.body))).toMatchObject({ revision: "a".repeat(64), targets: { scalar: "Otwórz plik" }, action: "draft" });
});

test("export of an unsaved draft explains how to save first", async () => {
  const { fetch } = setup();
  fireEvent.change(await screen.findByRole("textbox", { name: "Translation · Polish" }), { target: { value: "Nowy" } });
  fireEvent.click(screen.getByRole("button", { name: "Export TS" }));
  expect(screen.getByRole("alert").textContent).toContain("Save your changes before exporting");
  expect(fetch.mock.calls.some(([path]) => path.endsWith("export.ts"))).toBe(false);
});

test("approval reason cannot change while its submitted revision is saving", async () => {
  const { fetch, release } = setup({ unchanged: true, holdSave: true });
  const reason = await screen.findByRole("textbox", { name: "Reason for approving unchanged text" });
  fireEvent.change(reason, { target: { value: "Intentional invariant" } });
  fireEvent.click(screen.getByRole("button", { name: "Approve & next" }));
  expect(screen.getByRole("status").textContent).toBe("Saving…");
  try { expect((reason as HTMLInputElement).disabled).toBe(true); }
  finally { release(); }
  await waitFor(() => expect(screen.getByRole("status").textContent).toBe("Saved"));
  const write = fetch.mock.calls.find(([path]) => path.endsWith("/edits"));
  expect(JSON.parse(String(write?.[1]?.body)).reason).toBe("Intentional invariant");
});


test("catalog with native Qt locale opens the editor", async () => {
  setup({ targetLang: "de_DE" });
  expect(await screen.findByRole("textbox", { name: "Translation · German (Germany)" })).toBeTruthy();
});
