---
this_file: src_docs/md/3-formats/309-byte-preserving-edits.md
---

# 309. Byte-preserving edits: splice writers, diffs a reviewer can read, and provenance

A catalog under version control is reviewed through its diff. When a translator fixes one word, the reviewer expects to see one changed line, with the old word and the new one. When a program fixes one word, the reviewer often sees something else: every quote style changed, every empty element collapsed, the XML declaration rewritten and the final newline gone. The fix is in there somewhere. Nobody can find it, and nobody can be sure it is the only change.

This chapter is about writing localization files so that the diff shows the edit and nothing else. The technique matters most for large XML catalogs, where it is hardest, and it connects to a second concern that uses the same machinery: recording where each translation came from.

## Why ordinary serializers fail review

An XML library reads a file into a tree and writes the tree back out. The tree does not remember how the original file was spelled. Whether an attribute used single or double quotes, whether an empty element was written as a pair of tags or as one self-closing tag, whether an apostrophe was an entity, whether the file ended in a newline: all of that is lost at parse time and replaced by the library's own defaults on output.

Here is what that means for a real file. The German fixture from [chapter 302](302-qt-ts.md) was loaded with `lxml`, the translation of *Draft* was changed from *Entwurf* to *Entwürfe*, and the tree was written back. The unified diff:

```diff
@@ -1 +1 @@
-<?xml version="1.0" encoding="utf-8"?>
+<?xml version='1.0' encoding='UTF-8'?>
@@ -20 +20 @@
-        <translation type="unfinished">Entwurf</translation>
+        <translation type="unfinished">Entwürfe</translation>
@@ -32 +32 @@
-        <translation></translation>
+        <translation/>
@@ -56 +56 @@
-    <name></name>
+    <name/>
@@ -62 +62 @@
-</TS>
+</TS>
\ No newline at end of file
```

One edit produced five hunks. On a sixty-line fixture that is an annoyance. On a catalog of ten thousand messages, where every empty translation and every quoted attribute is rewritten, it is a diff no one reads. It also causes merge conflicts in lines that nobody edited, which is the subject of [chapter 703](../7-process/703-branches-and-merges.md).

The problem is old. Esselink (2000) warned that opening Windows resource files in different resource editors, or in different versions of the same editor, could change the structure of the files, and advised using the editor the publisher had used. Roturier (2015) observes that editing programs hide a file's complexity but are not suitable for every task, so bulk changes often end up in a text editor or a custom script. Both describe the same tension: tools that understand the format tend to rewrite it, and tools that preserve the text do not understand it.

## The splice writer

The way out is to parse for understanding and write by splicing. vexy-localizzy's TS writer, added in September 2026, works in four steps:

1. **Find the spans.** A tokenizer locates every `<message>` element in the original bytes as a start and end offset, skipping comments, CDATA sections, processing instructions and the DOCTYPE.
2. **Check the tokenizer.** On every write, the spans are compared with a full `lxml` parse of the same bytes. If the two disagree about where the messages are, the write fails instead of guessing.
3. **Render only what changed.** Each edited message is rendered in the document's own style, detected from the file: its XML declaration, indentation unit, line ending, whether it writes `&apos;` and `&quot;`, which empty elements it spells as tag pairs, and whether spaces before a line break are written as character references.
4. **Splice.** The rendered messages replace their spans. Every other byte of the file is copied unchanged. The `<TS>` start tag is rewritten only if one of its attributes changed, such as the target language.

The same edit made through the splice writer gives one hunk:

```diff
@@ -20 +20 @@
-        <translation type="unfinished">Entwurf</translation>
+        <translation type="unfinished">Entwürfe</translation>
```

The work log records the check at scale, on the four FontLab catalogs:

| Measurement | Result |
|---|---|
| Unedited messages re-rendered in their own style | 42,348 of 42,348 identical to the original bytes |
| `diff -U0` for a one-character edit in the German catalog, before the splice writer | 38,139 lines |
| The same diff with the splice writer | 5 lines |

A rendering that reproduces every unedited message exactly is the evidence that the renderer understands the file's style. The splice is the guarantee that even a renderer bug could only affect the messages that were meant to change.

The splice writer has a limit its authors recorded. It covers the path that edits an existing catalog, which is what `translate` and `upgrade` use. A second module, which prepares a new catalog from a template, still re-serializes the whole document; the work log notes that it was not changed in the same step. A byte-preserving writer is a property of a code path, not of a library, and each path that writes a catalog needs its own check.

Two tests tell you whether a writer has the property. The first is the identity test: write a catalog with no edits and compare the bytes with the input. vexy-localizzy applies it to every adapter, and its upgrade command applies it to the whole operation, since upgrading a catalog against itself must return identical bytes. The second is the one-edit test: change one translation and count the lines in `diff -U0`. Anything beyond the edited line is a defect in the writer, whatever the file format allows.

## Preserving bytes in other formats

TS is the hardest case because it is large and hand-formatted by `lupdate`. The same principle runs through every vexy-localizzy adapter, implemented to suit each format:

| Format | How edits stay local |
|---|---|
| PO | The original document is retained; unchanged round trips restore exact bytes |
| XLIFF | Inline content is exposed as XML fragments, and edits must keep the inline code identities |
| Android | Edits use Android quoting and whitespace rules; protected resources and placeholders stay untouched |
| i18next JSON | Edits replace only the selected string tokens; other values, including non-string ones, keep their bytes |
| TMX | Every original variant, property and provenance node is kept; exact-origin corpus entries refuse edits |

Two further rules protect the file on disk. Output is prepared and parsed before the destination is replaced, and the replacement is atomic, so a failed conversion leaves the previous file intact. And edits the adapter cannot make safely are refused before anything is written: removing a target without resetting its approval in XLIFF, or an unsupported structural change in any format.

## Provenance: where each translation came from

A small diff says what changed. It does not say why, or who proposed the new text. Once engines and memories fill catalogs, that second question matters as much as the first. The FontLab guide makes it a rule for machine drafts: pin the prompt, the model and the settings and record them beside the output, because a review that cannot name what it reviewed cannot be repeated.

vexy-localizzy records provenance in a sidecar file, not in the catalog. Every `translate` run writes a JSON report with the input digest and language pair, each memory file with its SHA-256 and unit count, counts per origin, and one row per message with its origin, match class, memory file, unit ids, glossary terms, the model requested and the model that answered. The upgrade command writes a report of the same kind for every message of a fresh catalog ([chapter 310](310-identity-and-upgrade.md)). The fl10n project keeps these reports next to the catalogs; the engine provenance for each shard of the Polish catalog, for example, is stored under `data-fontlab-cpp/i18n/upgrade/`.

The toolkit can also write provenance into the catalog, as an element Qt keeps as a message extra:

```xml
<extra-localizzy-origin>memory:de-fontlab-ui.tmx#Menu|Save;match=context</extra-localizzy-origin>
```

It does not do so by default. The reason is stated in its documentation and follows from this chapter: with the sidecar only, "shipped catalogs carry no extra diff". Provenance inside the file would turn every translation run into a change to thousands of messages, the same noise the splice writer exists to remove.

## Worked example: a reviewable correction pass

The FontLab review of September 2026 corrected 35 western strings and 663 Polish strings after the founder's review remarks. The work log describes the discipline that made the pass reviewable, and it generalizes to any correction pass:

1. Apply each correction against the exact prior target. The German, Spanish and French corrections were each checked against the text they replaced, so a correction written for an old draft could not overwrite a newer one.
2. Write through a byte-preserving writer, so the catalog diff contains only the corrected messages. The pass's script, `scripts/issue146.py` in the fl10n repository, loads and saves the catalogs through vexy-localizzy's TS adapter, whose save on a retained document is the splice writer.
3. Record every change in a ledger with its reason, separately from the catalog ([chapter 410](../4-terminology/410-ledgers-and-decisions.md) describes ledgers).
4. Verify the result independently: the validator reported 10,484 active messages and no unfinished ones per catalog, `lrelease` compiled all of them, and a scan for every retired term came back clean.
5. Let a second pass review the diff. In that review, an independent pass caught a non-idempotent rule that doubled a word, a genitive plural that a pattern had missed in twenty strings and four help passages, and one stray reflexive pronoun.

Step 5 is where the other steps pay off. A second reader has to see the edits to judge them, and nearly seven hundred edits are readable only when the diff holds nothing else.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 3)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 2.5.2)
- `WORK.md` and `scripts/issue146.py` in the fl10n repository
- [docs/formats.md](../8-toolkit/formats.md), [docs/memories.md](../8-toolkit/memories.md), [docs/upgrade.md](../8-toolkit/upgrade.md), `WORK.md` and `src/vexy_localizzy/formats/ts_splice.py` in the vexy-localizzy repository
- [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/) in the vexy-fontlab-writing-styleguide repository
- A local edit of `tests/fixtures/legacy_golden/inputs/ts/app_de.ts` through `lxml` and through `formats.ts`, recorded for this chapter
