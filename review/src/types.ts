// this_file: review/src/types.ts
export type Unit = { key: string; context: string; source: string; source_plural: string | null; target: string | null; disambiguation: string | null; notes: string[]; locations: string[]; state: string; slots: Record<string, string>; editable: boolean; max_length: number | null };
export type Summary = { id: string; source_lang: string; target_lang: string | null; total: number; approved: number; revision: string };
export type Catalog = Summary & { units: Unit[] };
export type Asset = { id: string; name: string };
export type Suggestion = { source: string; target: string; provenance: string };
export type Finding = { rule_id: string; message: string; severity: string };
export type Quality = { checking: boolean; error: string; findings: Finding[] };
export const stateLabel: Record<string, string> = { approved: "Approved", needs_review: "Needs review", translated: "Not reviewed", untranslated: "Not reviewed", vanished: "Excluded" };
export function language(code: string | null) {
  if (!code?.trim()) return "Unspecified";
  try { return new Intl.DisplayNames(["en"], { type: "language" }).of(code.replaceAll("_", "-")) ?? code; }
  catch (error) { if (error instanceof RangeError) return code; throw error; }
}
