---
this_file: src_docs/md/2-engineering/202-world-ready-design.md
---

# 202. World-ready design: separating code from text, data from presentation

A program that works only in its first language is not a neutral starting point. It is full of decisions that were made without being noticed: the language of every message, the order of day and month, the character that separates decimals, the assumption that a word ends at a space and that a line runs from left to right. World-ready design is the practice of finding those decisions and moving each one out of the code into data that the program reads at run time. This chapter explains why that separation pays, which kinds of data have to be separated from which, and how to replace a compile-time language decision with a runtime one.

## Why localizing the code does not scale

In 1994 Sandra Martin O'Donnell described the two ways teams then adapted software for another country. The first removed the old culture's code and put the new culture's code in its place. The second kept both behind a switch: `if (french) ... else ...`, growing into a chain of `else if (swedish)` with every new market. She showed a small C program in three versions, American, French and bilingual, and pointed out that every input and output statement had to be duplicated. Her verdict still holds:

> "Localizing software simply replaces one hard-coded set of rules with another. A better approach is to remove the hard-coded rules that prevent software from traveling across borders." (O'Donnell 1994)

Her list of costs reads like a post-mortem of many later projects. The localized version is always late, because the work cannot start until the code is stable; she calls a delay of six to twelve months not unusual. Each new language means reopening, recompiling and retesting the code. Six releases in two languages become twelve code bases to maintain. Local engineers "improve" their copy, so the product behaves differently in different countries. And programmers cost more than translators. The internationalized alternative changes the equation: the data still has to be localized, but the code does not.

Microsoft's *Developing International Software* (2002) makes the same argument in terms of a single binary: one executable for every language edition, no conditional compilation, no separate source trees, patches that apply to all languages at once. The book reports what that bought the Windows XP team: the German edition shipped the same day as the English one, and Chinese, Japanese, Korean and several European editions within 21 days, where Japanese Windows 3.1 had trailed English by more than a year. It also gives the arithmetic of neglect: every localizability defect left in the core code is paid once per market, so with 24 markets a defect can cost up to 24 times its original fix.

## What a first-language program assumes

Before you can separate anything, you have to see it. The assumptions hide in plain sight because they are true for the people who wrote the code. Both books give lists; merged and brought up to date, they look like this:

| Assumption in the code | What breaks | Where this book treats it |
|---|---|---|
| Messages are string literals in source files | Nothing can be translated without editing code | [203](203-externalizing-strings.md) |
| Sentences can be built from fragments | Word order, gender and case in the target language | [204](204-placeholders-and-grammar.md) |
| A character is a byte | Truncation mid-character, corrupted text | [104](../1-foundations/104-characters-and-encodings.md) |
| Dates, numbers and money have one format | Wrong values read, not just wrong punctuation | [106](../1-foundations/106-numbers-dates-and-units.md) |
| Text runs left to right | Mirrored layouts, mixed-direction values | [208](208-mirroring-and-rtl.md) |
| One font covers every script | Empty boxes, wrong shaping | [209](209-rendering-and-opentype.md) |
| A label fits the space the English label needed | Clipping, overlap, lost information | [109](../1-foundations/109-space-and-growth.md) |
| Words are separated by spaces | Wrapping, search and word counts in Thai or Japanese | [108](../1-foundations/108-scripts-direction-and-fonts.md) |

O'Donnell's shortest formulation of the third row, "Character does not equal byte", was written when the problem was 8-bit code pages and multibyte Asian encodings. Unicode changed the details, not the lesson: a code point is still not a grapheme, and a grapheme is still not a glyph.

## Four kinds of resource

Moving text out of the code is necessary but not sufficient. Dr International's chapter on localizability makes a distinction that most teams learn the hard way: not everything that looks like text is text for translation. The book sorts a program's strings and data into four categories.

| Category | Examples | May a translator change it? |
|---|---|---|
| User interface | Menus, dialogs, messages, tooltips, status text | Yes, freely |
| Adaptation | Default fonts, locale data, folder and account names | Only with engineering knowledge; a wrong value changes behavior |
| Debug | Trace messages, assertions, developer diagnostics | No; they stay in the developer's language |
| Functional | Registry and preference keys, command tokens, names of shared objects, strings passed between components | Never; translation breaks the product |

The failure mode is mixing the categories in one resource file. A translator who cannot see the code cannot tell a menu label from a command token, and the book's examples are memorable: a command string "Open" that became "Ouvrir" and stopped working, the name of a mutex or event shared between two binaries, code that compares an account name against the English "SYSTEM" and fails on a localized operating system. The remedy is structural. Keep the user-interface and adaptation categories in the translatable resources, keep the debug and functional categories somewhere translators never see, and keep the adaptation category as small as possible by asking the platform for values such as folder names instead of storing them.

The FontLab writing guide gives the modern version of the same list for a font editor. Its interface-strings page tells reviewers to leave untouched date-pattern letters, preference keys, file and folder names, command-line switches, OpenType feature tags, glyph names, Python identifiers, paths and URLs, and to treat a word in capitals, a word with the `_` separator or a run-together word as an identifier until an engineer says otherwise. Debug-only messages stay in English, so that a developer can read a bug report from any locale. When such a string reaches the translation catalog anyway, the reviewer records it as a source defect rather than translating it. The catalog is the wrong place for it, and the fix belongs in the code.

## Replace compile-time language with runtime data

The classic world-readiness mistake is to decide language behavior when the program is built. Dr International quotes a start-up routine that uses the preprocessor for it:

```c
#ifdef JAPAN
#define NO_SPELL_CHECKER
#define EASTASIA
#define DEFAULT_PAPER_SIZE 2 // A4
#endif
...
#ifndef NO_SPELL_CHECKER
InitSpellChecker();
#endif
#ifdef EASTASIA
InitIME();
#endif
```

Every language edition is a different binary, every fix has to be checked in every configuration, and, as the book warns, developers forget to update the code inside the `#ifdef` when they change the code around it. The rewrite reads the same decisions from data at start-up:

```c
typedef struct _LOCINFO {
    int  fSpellChecker;
    int  fUsesIME;
    int  DefaultPaperSize;
    LCID lcidDefaultLocale;
} LOCINFO;

LOCINFO locinfo;
GetLocInfo(&locinfo);            /* implemented in a language resource */
if (locinfo.fSpellChecker) InitSpellChecker();
if (locinfo.fUsesIME)      InitIME();
```

The Win32 types are historical; the pattern is not. Three things changed since 2002 and make it easier. Locale data now comes from a shared repository, CLDR, instead of each vendor's tables ([105](../1-foundations/105-locales-and-cldr.md)). Formatting libraries such as `Intl` in JavaScript and `QLocale` in Qt take a locale as an argument, so a program can format one value for German and another for Polish in the same process; O'Donnell listed the process-global locale of the 1990s C library, one locale at a time and no tagging of data, among the limits of the model she described. And the settings are now understood to be several, not one. The FontLab runtime review asks the tester to record the interface language, the formatting locale, the input method, the document language, the time zone and the currency separately, because an English interface can coexist with Polish number formatting. A design that derives all of them from one language setting has reintroduced a hard-coded rule.

Two design rules follow. First, choose behavior from data, and choose data from explicit settings, not from geography or from the interface language. Second, keep features that differ by market in separate, optional modules. Dr International's example is the spelling checker: the engine stays constant, the dictionaries ship as data files, and a language without a checker simply has no dictionary.

## Organize the team around one product

The last part of world-ready design is not code. Dr International describes Microsoft's early split into domestic and international teams with separate managers and priorities, which produced an us-and-them mentality and code that only international developers ever fixed. The book's rules for managers are short: educate everyone on internationalization, hold every developer responsible for the international behavior of their features, and develop at least one localized or pseudo-localized edition alongside the source-language edition. It adds three practices that remain sound:

- one source tree and one bug database for all languages, so a defect found in the Polish build is a defect in the product;
- no language-specific `#ifdef`, and no fixes that apply "only to international builds";
- a localization kit that lets translators build and check their work without the source code.

The toolkit behind this book follows the same line from the other side. The toolkit design begins with the observation that the FontLab repositories were not instrumented for localization, and its first command, `localizzy qt scan`, reports which user-facing strings are marked, which are not and which are marked wrongly, as a coverage figure that a continuous-integration gate can ratchet upward over time. That audit is described in [205](205-qt-instrumentation.md). The point here is that world-readiness can be measured, and that the measurement belongs in the build, not in a review at the end.

## Sources

- Sandra Martin O'Donnell, *Programming for the World: A Guide to Internationalization*, 1994 (chapter 3, designing for the world; chapter 4, obsolete facts about characters; chapter 8, limits of the locale model)
- Dr International, *Developing International Software*, second edition, 2002 (chapter 2, designing a world-ready program; chapter 7, isolating localizable resources)
- [docs/scanning.md](../8-toolkit/scanning.md) and [docs/design/architecture.md](../8-toolkit/design/architecture.md) in the vexy-localizzy repository
- [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/) and [localization/runtime-review](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/runtime-review/) in the vexy-fontlab-writing-styleguide repository
