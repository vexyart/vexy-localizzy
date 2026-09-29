---
this_file: src_docs/md/3-formats/302-qt-ts.md
---

# 302. Qt Linguist TS: contexts, numerus forms, states and what lupdate rewrites

A Qt `.ts` file is the translation source for a Qt application. `lupdate` writes it by scanning C++, `.ui` and QML files; a translator or an engine fills it; `lrelease` compiles it into a binary `.qm` file that `QTranslator` loads at run time. The `.ts` file is XML, one file per target language, and it is the file a Qt team commits to version control. The `.qm` file is a build artifact. The research corpus and the fl10n specification agree on that division: commit `.ts`, ignore `.qm`, and run `lrelease` in continuous integration or packaging rather than in the developer's inner loop.

This chapter reads the format as a data model. The instrumentation that produces it, `tr()`, `Q_OBJECT`, the NOOP macros and translator comments in code, belongs to [chapter 205](../2-engineering/205-qt-instrumentation.md), and the toolchain commands to [chapter 206](../2-engineering/206-qt-toolchain-and-runtime.md).

## The shape of a TS file

A small catalog shows almost everything. This German file is a test fixture in the vexy-localizzy repository:

```xml
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="de_DE" sourcelanguage="en">
<context>
    <name>MainWindow</name>
    <message>
        <source>Save &amp; close</source>
        <translation>Speichern &amp; schließen</translation>
    </message>
    <message>
        <source>Draft</source>
        <translation type="unfinished">Entwurf</translation>
    </message>
    <message>
        <source>Gone</source>
        <translation type="vanished">Weg</translation>
    </message>
    <message numerus="yes">
        <source>%n file(s)</source>
        <translation>
            <numerusform>%n Datei</numerusform>
            <numerusform>%n Dateien</numerusform>
        </translation>
    </message>
</context>
</TS>
```

The root carries two language attributes. `sourcelanguage` names the language of every `<source>`; `language` names the target. Messages are grouped under `<context>` elements, and each context has a `<name>`. For code instrumented with `tr()` inside a `Q_OBJECT` class, the context name is the class name, because that is the context Qt uses when it looks the string up at run time.

A `<message>` holds more than the fixture shows. The element ownership table in the vexy-localizzy upgrade documentation lists the children Qt writes, in Qt's own order:

| Element | What it holds |
|---|---|
| `<location>` | File and line where `lupdate` found the string; may be absolute or relative |
| `<source>` | The source text, a literal from code |
| `<oldsource>` | The previous source, kept when a changed string was matched to an old one |
| `<comment>` | The disambiguation string, the second argument of `tr()` |
| `<oldcomment>` | The previous disambiguation |
| `<extracomment>` | The developer note written as `//:` in code |
| `<translatorcomment>` | A note the translator adds in Linguist |
| `<translation>` | The target text, or `<numerusform>` and `<lengthvariant>` children |
| `<userdata>`, `<extra-*>` | Metadata for downstream tools; `//~ key value` in code becomes an `extra` element |

Two attributes complete the message: `numerus="yes"` for a plural message, and an optional `id` for messages that use `qtTrId()` and explicit IDs written with `//=` in code.

The distinction between `<comment>` and `<extracomment>` matters more than its size suggests. The comment is part of the lookup key: `tr("Name:")` and `tr("Name:", "recipient")` are two messages with two translations. The extra comment is guidance only, visible to the translator and invisible to the lookup. Research on Qt recommends using `//:` notes for explanation and keeping the disambiguation argument for genuine sub-context, such as *Open* as a verb and *Open* as an adjective.

## Identity: what makes two messages the same

Qt resolves a translation from a tuple: context, source text, disambiguation and, for plurals, the count. A message in a `.ts` file is therefore identified by context, source and comment. Locations never count. When a message carries an `id`, that id identifies it instead.

This key has a consequence that surprises teams coming from key-based web formats. The source text is part of the identity, so fixing a typo in English creates a new message. The old translation does not follow it automatically; something has to recognize that *Horizonal* and *Horizontal* are the same message. [Chapter 310](310-identity-and-upgrade.md) is about that recognition.

The context is also part of the identity, and it drifts silently. If a widget subclass forgets `Q_OBJECT`, its run-time context is the base class, while `lupdate` files its strings under the subclass name. The lookup never matches and the interface falls back to English. The file itself looks correct. Only a running application shows the fault.

## Numerus forms are positional

A plural message holds one `<numerusform>` per plural form of the target language, and the forms carry no labels. Their order is the order of Qt's own rule for the language. Nothing in the XML says which form is "one" and which is "other"; the reader has to know the rule.

The number of forms also comes from Qt, and here the sources disagree. The fl10n format notes (`docs/formats/ts.md`) state that the forms align with CLDR categories and give French three forms (one, many, other) and Russian four (one, few, many, other). The numerus table in vexy-localizzy (`formats/qt_numerus.py`), which was read from Qt's `numerus.cpp` on the 5.15 branch, gives different counts, and the fl10n research synthesis agrees with it for Russian:

| Language | Qt 5.15 numerus forms | CLDR cardinal categories |
|---|---|---|
| German | 2 | one, other |
| French | 2 | one, many, other |
| Polish | 3 | one, few, many, other |
| Russian | 3 | one, few, many, other |
| Japanese | 1 | other |
| Arabic | 6 | zero, one, two, few, many, other |

The FontLab Polish catalog was checked by a three-form plural gate and compiled fully by `lrelease`, which is consistent with the Qt count. The safe rule is to take the count from Qt, not from CLDR, and to check it for the Qt version you ship: `lupdate -list-languages` lists the supported languages with their expected plural-form counts. A `.ts` file with the wrong number of forms is a file Qt cannot use correctly.

One more trap sits in the source language. English also has plural forms. Without an English `.ts` carrying them, a message such as `%n file(s)` displays the literal "file(s)" in the English build, because nothing tells Qt how to choose between "file" and "files". The research lists this among the common Qt pitfalls; Qt 6 handles it with a dedicated plurals catalog.

## States, and what the tools do with them

The `type` attribute of `<translation>` carries the review state:

| `type` | Meaning | Compiled by `lrelease`? |
|---|---|---|
| absent | Finished | Yes |
| `unfinished` | New, changed or not yet approved | No, by default the source text is shown |
| `vanished` | The source string no longer exists in code (Qt 5 and later) | No |
| `obsolete` | The older marking for a string removed from code | No |

`lrelease` emits only finished translations. An unfinished translation falls back to the source at run time, which makes the state field a release control, not a comment. Several `lrelease` options turn this into a gate: `-nounfinished` excludes unfinished text, `-fail-on-unfinished` stops the build, and `-markuntranslated` prefixes untranslated strings in a QA build so that they are easy to spot on screen.

Qt has fewer states than a translation workflow needs. There is no separate "needs review" and no "approved by a second reader". The vexy-localizzy adapter maps Qt's finished state to `translated` and writes both `untranslated` and `needs_review` as unfinished; when a project needs richer approval states, it keeps them in the canonical JSON catalog rather than in the `.ts` file ([chapter 307](307-the-canonical-model.md)).

### What lupdate rewrites

`lupdate` does not create a fresh file each time. It performs a smart merge: it keeps existing translations, appends new messages as unfinished, and marks messages whose source disappeared as vanished. With `-no-obsolete` it drops them instead. Its merge heuristics try to rescue translations when a source string changed slightly; the `-disable-heuristic` option names three of them, `sametext`, `similartext` and `number`. The format has a place for the evidence of such a pairing: `<oldsource>` and `<oldcomment>` hold the previous source and disambiguation, so a translator can see what changed before approving the carried-over text.

Two options exist mainly for version control. `-locations none` or `-locations relative` stops line numbers from changing in every message whenever code moves, and `-no-ui-lines` does the same for `.ui` files. The fl10n specification runs `lupdate` with `-locations none -no-obsolete`, so that the committed catalog changes only when strings change.

The merge happens in place. That is convenient for a single developer and inconvenient for a reviewed catalog: the command writes no list of what it dropped, no report of which translations it matched by heuristic, and it cannot consult a translation memory. [Chapter 310](310-identity-and-upgrade.md) describes the alternative the FontLab project adopted, which keeps `lupdate` as the extractor and moves the merge into a separate step with a report.

## Worked example: preparing a Polish plural

Suppose a German catalog contains this message and you are creating the Polish catalog from it:

```xml
<message numerus="yes">
    <source>%n glyph(s)</source>
    <translation>
        <numerusform>%n Glyphe</numerusform>
        <numerusform>%n Glyphen</numerusform>
    </translation>
</message>
```

Copying the structure is wrong. Qt expects three forms for Polish, so the Polish message needs three `<numerusform>` elements in the order of Qt's Polish rule: one glyph, a few glyphs, many glyphs. A tool that clones the German shape produces a two-form Polish message that compiles and then shows the wrong ending for five or more. The vexy-localizzy upgrade command therefore sizes every numerus message by the target language's Qt count, and treats the count in the fresh `lupdate` output as meaningless when the file has no `language` attribute, because `lupdate` then writes two slots regardless of the target.

Check three things whenever a tool prepares a `.ts` file for a new language:

1. The `language` attribute is set, so that tools and `lrelease` know the target.
2. Every numerus message has exactly the Qt count of forms, and none is empty.
3. Every `%n`, `%1` and `&` accelerator in the source appears in each form where the language needs it.

The FontLab catalogs pass the same gates at scale: about ten thousand five hundred active messages per language, all finished, compiled by `lrelease` with no unfinished entries.

## Sources

- `research/02-localizing-qt-cpp-applications.md` and `research/05-format-conversion-cicd-and-continuous-localization.md` in the fl10n repository
- `spec/03.md`, `docs/formats/ts.md` and `WORK.md` in the fl10n repository
- `docs/formats.md`, `docs/upgrade.md`, `src/vexy_localizzy/formats/qt_numerus.py` and `tests/fixtures/legacy_golden/inputs/ts/app_de.ts` in the vexy-localizzy repository
