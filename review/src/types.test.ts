// this_file: review/src/types.test.ts
import { expect, test } from "vitest";
import { language } from "./types";

test.each(["de_DE", "en_US", "zh_Hant_TW"])("Qt locale %s is displayed without changing its stored value", code => {
  expect(language(code)).toBe(language(code.replaceAll("_", "-")));
});
test.each(["", null])("missing locale %s has a readable label", code => {
  expect(language(code)).toBe("Unspecified");
});
test("unrecognized locale syntax remains visible instead of crashing review", () => {
  expect(language("not/a/locale")).toBe("not/a/locale");
});
