---
this_file: src_docs/md/3-formats/index.md
---

# Part 3. Formats and data

Every translated string lives in a file, and every file format decides what travels with the string: its context, its plural forms, its placeholders and its review state. This part reads the formats of software localization as data models. It covers Qt TS, gettext PO, both dialects of XLIFF, the application formats of the web, Android and Apple, and the TMX and TBX exchange formats for memories and terminology. It then turns to the operations that cross formats: a canonical model that makes every conversion's loss visible, the conversion tools and when to write your own, edits that change only the bytes they mean to change, and the upgrade that carries reviewed translations onto a fresh catalog without losing the ones it cannot place.

- [301. What this part knows](301-what-this-part-knows.md)
- [302. Qt Linguist TS: contexts, numerus forms, states and what lupdate rewrites](302-qt-ts.md)
- [303. Gettext PO: msgctxt, plural headers, fuzzy and the tooling around it](303-gettext-po.md)
- [304. XLIFF 1.2 and 2.1: the interchange format and its two dialects](304-xliff.md)
- [305. JSON, Android XML and Apple strings: the application formats](305-json-android-apple.md)
- [306. TMX and TBX: exchanging memories and terminology](306-tmx-and-tbx.md)
- [307. The canonical model: one typed representation and the loss every conversion accepts](307-the-canonical-model.md)
- [308. Conversion tools: lconvert, Translate Toolkit, Okapi and when to write your own](308-conversion-tools.md)
- [309. Byte-preserving edits: splice writers, diffs a reviewer can read, and provenance](309-byte-preserving-edits.md)
- [310. Identity and upgrade: matching messages across versions, retired strings, fresh catalogs](310-identity-and-upgrade.md)
