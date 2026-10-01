---
this_file: src_docs/md/2-engineering/203-externalizing-strings.md
---

# 203. Externalizing strings: keys, contexts, comments and the message-key model

Every localization system, whatever its age or platform, reduces to one lookup: given an identifier for a message and the active language, return the text to display. Systems differ in what the identifier is, how much context travels with it and what happens when the lookup fails. Those three choices decide whether a translator can do good work, whether a source edit silently discards finished translations, and whether a missing translation is visible or invisible. This chapter explains the message-key model in its main variants and shows how to give each message an identity and a context that a translator, human or machine, can use.

## The lookup, then and now

The mechanism has been stable for thirty years; the vocabulary has changed. In O'Donnell's 1994 account of the X/Open messaging calls, a program opens a message catalog for the current locale with `catopen`, asks for a message with `catgets(catd, set_id, msg_id, default)` and closes the catalog when it is done. The identifier is a pair of integers, a set number and a message number, and the call carries a default string that the program displays if the catalog or the message is missing. She names the integer identifiers as the most annoying part of the system and recommends mnemonic labels defined in a header, compiled to numbers by a preprocessor.

Two of her recommendations survived every later system. Keep the default text in the call, so the source code stays readable and a user whose catalog failed to load still gets a real message. And make that default a real message: a fallback that says only "Failure" helps nobody.

Roturier (2015) describes the gettext workflow that replaced catalogs of numbers with catalogs of source strings, in five steps: mark the translatable strings in the source code, extract them into a translation-ready format, translate them, compile the translated resource, and load it into the application. His example uses Django, where `ugettext` is imported under the name `_` and templates mark text with `{% trans %}` blocks. He also shows what happens when you skip the marking step: running `xgettext` over unmarked code extracts every string it finds, including internal words that no user ever reads.

The research corpus behind this book states the modern general form with Qt as its most complete example. Qt resolves four values into one string:

```
(context, sourceText, disambiguation, n)
```

The context partitions messages into buckets, usually by class name. The source text is the English itself. The disambiguation separates two identical source strings within one context. And `n` selects a plural form. Gettext adds an optional `msgctxt` to its otherwise flat namespace of source strings ([303](../3-formats/303-gettext-po.md)); web libraries use a key that the developer chooses and a separate file per language ([207](207-web-and-typescript.md)).

## Choose what identifies a message

The identifier is either the source text or a key that the developer invents. Each choice has a cost, and the sources disagree about which cost is worse.

| Identifier | Examples | Strength | Cost |
|---|---|---|---|
| Source text | Qt `tr("Open")`, gettext `msgid`, natural-language keys on the web | Readable code; the English is its own fallback | Any edit to the English, even a typo fix, creates a new message and orphans the old translation |
| Structured key | `checkout.button.submit`, Qt `qtTrId()` with `//=` IDs | Text changes are catalog edits only; the key survives rewrites and carries history in a translation management system | Developers work in two files; unused keys accumulate; the English must be looked up |
| Hash of the source | Lingui and FormatJS content hashes | Short, stable IDs generated at build time | The hash still changes when the text changes |

The research corpus records the disagreement openly. One source concludes that structured keys are the better choice for any long-lived project; another credits natural-language keys with better ergonomics and treats their brittleness as a problem that translation memory can repair. The reconciled rule it proposes is a threshold: use structured keys when the project has more than two languages, more than one translator or a planned life of more than six months, and accept natural keys for small, content-led applications.

If you use the source text as the key, take the consequence seriously. The FontLab writing guide spells it out for Qt: rewording a shipped English string orphans its translation in every catalog, where the old entry becomes *vanished* and a new unfinished entry appears. A source edit therefore needs a behavioral reason and a record. Two strings that differ only in a trailing space, an ellipsis or a capital letter are two messages, and the difference carries meaning: the ellipsis announces a dialog, the trailing space means the application appends text. Recovering translations across such edits is the job of an upgrade step ([310](../3-formats/310-identity-and-upgrade.md)), and `localizzy upgrade` exists because the naive merge loses them.

## One text, several messages

The most expensive externalization mistake looks like thrift: one resource used wherever the same English word appears. Dr International (2002) warns against all-purpose strings such as "none", "blue" or "first", because European adjectives and nouns can have four to fourteen forms. Spanish "first" alone is *primero*, *primera*, *primer*, *primeros* or *primeras*, depending on a noun the string never mentions. The book's remedy is one string per context: `Menu_open`, `Dialog_open`, `Button_open`.

O'Donnell adds the reverse argument, from the translator's side. Her example is a German catalog in which one vague English "not found" becomes three precise messages, because German users expect the difference. That is only possible if the program has three messages to begin with:

> "Translators can not add new messages to a catalog; they can only translate the ones that already exist." (O'Donnell 1994)

The rule that follows is simple. A message is a meaning in a place, not a sequence of letters. Reuse a resource only after checking that the meaning, the grammatical role and the surface are the same. The FontLab guide lists the English words that most often fail this test in a graphics application: *None*, *All*, *Auto*, *Default*, *Copy*, *Scale*, *Fill* and *Close*, each a noun, a verb or an adjective depending on the control.

## Give each message context

Context is the lever that improves every translation, and the research corpus makes it the first principle of the whole field: the fix for a bad translation is almost always more context. The mechanisms differ by platform.

| Mechanism | Part of the lookup key? | What it is for |
|---|---|---|
| Qt context (class name) | Yes | Separates the same text in different parts of the program |
| Qt disambiguation, the second `tr()` argument | Yes | Separates two identical texts in one context |
| Qt `//:` translator comment | No | Explains meaning, trigger and placeholders to the translator |
| Qt `//~ key value` | No | Metadata for tools, stored in the catalog and hidden in Linguist |
| gettext `msgctxt` | Yes | The gettext equivalent of disambiguation |
| gettext `#.` extracted comment | No | Translator note extracted from the source (`xgettext -c`) |
| Angular `i18n` attribute: meaning, description and `@@` ID | Meaning and ID only | Meaning separates messages; description informs the translator |

Here is a worked example. A font editor has an *Open* button on a toolbar and a contour property that reports whether a path is open or closed. Both say "Open" in English, and in one class they would collide.

```cpp
//: Toolbar button. Opens a font file from disk.
openButton->setText(tr("Open", "command"));

//: Contour state shown in the Info panel. The opposite is "Closed".
stateLabel->setText(tr("Open", "contour state"));
```

After `lupdate`, the catalog carries the two meanings as two messages. The disambiguation lands in `<comment>`, where it is part of the key, and the translator note lands in `<extracomment>`, where it is not:

```xml
<message>
    <source>Open</source>
    <comment>contour state</comment>
    <extracomment>Contour state shown in the Info panel. The opposite is "Closed".</extracomment>
    <translation type="unfinished"></translation>
</message>
```

German can now write *Öffnen* for the command and *Offen* for the state, and a machine translation engine that receives the comment has the same chance ([603](../6-machine-translation/603-context-engineering.md)). Note the asymmetry: changing the comment text later does not change the lookup, but changing the disambiguation does, because it is part of the key.

A comment helps only when it answers a question the translator would otherwise have to guess. Roturier observes that comments are routinely missing because developers have no time or do not feel qualified, and that the result is mistranslated ambiguous strings and truncated labels found only in quality assurance, although more time spent preparing the source strings would have prevented them. The FontLab guide proposes a message contract for each resource: its stable identity and source revision, the trigger that shows it, its purpose, the meaning and range of each value it receives, the related messages, and the surface it appears on with the available space. It states the limit of any single aid clearly: a screenshot alone does not explain a zero case, and a count alone leaves the translator guessing whether it counts fonts, glyphs or files.

## When the lookup fails

A lookup can fail in several ways, and a good design keeps them distinguishable. Baldurs (2025) recommends a fallback chain of requested locale, then fallback locale, then the key itself, with each missing key logged once. Dr International's advice on fallback languages is more careful. The only safe assumption about the user's language is the operating system's interface language. If the program has no translation for that language, it should ask the user which language to use rather than fall back to English by reflex: a Belgian user with a French interface probably reads Dutch as a second language, not English.

The FontLab guide adds the testing view. An intentionally empty message, an absent entry, an unloaded catalog and a fallback are four different outcomes, and a test that asserts only "the result is a string" passes for all of them. An intelligible fallback keeps a task usable; it is not a reviewed translation and should not raise a coverage figure. The runtime side of this, missing catalogs and language switching, is the subject of [206](206-qt-toolchain-and-runtime.md) and [210](210-testing-world-readiness.md).

## Sources

- Sandra Martin O'Donnell, *Programming for the World: A Guide to Internationalization*, 1994 (chapter 9, program messages)
- Dr International, *Developing International Software*, second edition, 2002 (chapter 6, fallback language; chapter 7, string handling)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (chapter 2, software strings and files; chapter 3, internationalization)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025 (chapter 3, fallbacks; chapter 8, Angular message markers)
- [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/) and [localization/message-contracts](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/message-contracts/) in the vexy-fontlab-writing-styleguide repository
- [docs/upgrade.md](../8-toolkit/upgrade.md) in the vexy-localizzy repository
