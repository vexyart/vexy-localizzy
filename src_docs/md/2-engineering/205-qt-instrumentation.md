---
this_file: src_docs/md/2-engineering/205-qt-instrumentation.md
---

# 205. Qt instrumentation: tr(), contexts, disambiguation, NOOP macros and .ui files

Qt's translation system is one of the most complete in general use, and one of the easiest to break without noticing. A string that is marked wrongly does not fail to compile and does not crash. It is either missing from the catalog or filed under a context that the running program never asks for, so the interface shows English although a translation exists. This chapter explains how Qt finds a message, which macro to use in which situation, how Designer forms take part, and how to audit a large C++ code base for the mistakes that matter. The tools that turn the marked source into catalogs and load them at run time follow in [206](206-qt-toolchain-and-runtime.md); the catalog format itself is [302](../3-formats/302-qt-ts.md).

## Two readers of one call

A call to `tr()` has two readers, and instrumentation is correct only if both agree. The first reader is `lupdate`, a static analyzer. It walks the source files and Designer forms, recognizes the translation markers and writes each message to a `.ts` catalog under a context. It never compiles or runs the code, so it can only record what is literally written: `tr(someVariable)` gives it nothing to extract, silently.

The second reader is the compiled program. In a class that declares `Q_OBJECT`, the meta-object compiler generates a static `tr()` that calls `QCoreApplication::translate()` with the class name as the context. At run time, the program asks the installed translators for the pair of context and source text, plus the disambiguation and count when present. The Qt documentation, quoted in the research corpus, states the rule that both readers depend on:

> "The translation context for QObject and each QObject subclass is the class name itself. Developers subclassing QObject must use the Q_OBJECT macro... If Q_OBJECT is not used in a class definition, the context will be inherited from the base class."

Two practical rules follow. Pass literal, UTF-8 string constants to every marker. And make sure the context that `lupdate` writes is the context the program will ask for.

## Choose the right marker

Qt offers several markers because strings live in several kinds of place: inside `QObject` classes, inside ordinary C++ classes, in free functions and in static tables. The research corpus condenses them into one table.

| Form | Use it for | Extracted? | Translates at run time? |
|---|---|---|---|
| `tr("...")` in a `Q_OBJECT` class | The default; context is the class name | Yes | Yes |
| `QCoreApplication::translate("Ctx", "...")` | Free functions, or an explicit context | Yes | Yes |
| `Q_DECLARE_TR_FUNCTIONS(Ctx)` then `tr("...")` | Classes that are not `QObject`s | Yes | Yes |
| `QT_TR_NOOP("...")` | Static data inside a class | Yes, class context | No, returns the C string |
| `QT_TRANSLATE_NOOP("Ctx", "...")` | Static data outside any class | Yes | No |
| `QT_TRANSLATE_NOOP3("Ctx", "...", "disamb")` | Static data with disambiguation | Yes | No |
| `QT_TR_N_NOOP`, `QT_TRANSLATE_N_NOOP` | Static data with a plural count | Yes | No |
| `QT_TRID_NOOP("id")` with `qtTrId("id")` | ID-based translation | Yes | `qtTrId` does |

For classes that should not carry the weight of `QObject`, such as data models, utility classes and plain structs, `Q_DECLARE_TR_FUNCTIONS(Context)` adds an inline static `tr()` that forwards to `QCoreApplication::translate` with a fixed context. The research corpus notes a disagreement among its source documents: one routes all non-`QObject` strings through `QT_TRANSLATE_NOOP` and does not mention `Q_DECLARE_TR_FUNCTIONS` at all, while the others present it as the documented solution. The documented macro is the simpler choice.

Namespaces need care in the extractor. Without include paths, `lupdate` may not resolve a qualified class name, prints "Qualifying with unknown namespace/class", and files the strings under a shortened context that the program never uses. Pass the include directories with `-I` so the extractor sees what the compiler sees.

## Defer what is built before the application exists

Static tables are the next trap. A `static const QString` initialized with `tr()` runs during static initialization, before `QApplication` exists and before any translator is installed. It captures the source text once and never changes, even after the user switches language.

```cpp
// Wrong: evaluated once at start-up, before any translator is installed.
static const QString kUntitled = QObject::tr("Untitled");

// Right: store the marked literal, translate on every use.
class FontListModel : public QAbstractTableModel {
    Q_OBJECT
    static constexpr const char *kHeaders[] = {
        QT_TR_NOOP("Family"), QT_TR_NOOP("Style"), QT_TR_NOOP("Glyphs")
    };
public:
    QVariant headerData(int s, Qt::Orientation o, int role) const override {
        if (role == Qt::DisplayRole && o == Qt::Horizontal)
            return tr(kHeaders[s]);
        return {};
    }
};
```

The NOOP macro makes the literal visible to `lupdate` and returns it unchanged; `tr()` translates it later, on every call, so the header follows a language change ([206](206-qt-toolchain-and-runtime.md)). Outside a class, use `QT_TRANSLATE_NOOP` with an explicit context and `QCoreApplication::translate` with the same context. The drafts behind the research corpus describe `QT_TR_NOOP` outside a class differently, one loosely as usable for global variables and another strictly as unreliable there; the strict reading is the safe one, because the macro has no class to take its context from.

## Annotations and Designer forms

Qt's extractor reads four kinds of annotation near a marked string, and each has a different job.

```cpp
//: Shown in the status bar after a successful export. %1 is a folder path.
statusBar()->showMessage(tr("Exported to %1").arg(folder));

//~ max-length 24
okButton->setText(tr("Apply", "apply the transform, not a preference"));
```

- `//:` is a translator note. It appears in Qt Linguist and in the catalog's `<extracomment>`, and it is not part of the lookup.
- The second argument of `tr()` is the disambiguation. It is part of the lookup key, so changing it detaches existing translations.
- `//~ key value` stores metadata for tools, under a key name you choose, as an `extra` field that Linguist does not show.
- `//=` and `//%` supply the ID and the source text for the ID-based `qtTrId()` workflow.

The research corpus recommends `//:` for guidance and the disambiguation argument only for real sub-contexts, such as a verb and an adjective that share a spelling. [203](203-externalizing-strings.md) explains why the difference between a comment and a key matters when strings change.

Designer `.ui` files take part in the same extraction. They are XML, and `lupdate` extracts every `<string>` that is not marked `notr="true"`. The generated `retranslateUi()` function reapplies the translations to a form, which is what makes a language switch work for forms without hand-written code. Two mistakes are common. A visible label marked `notr="true"` never reaches the translator. And a label whose text is set in C++ after `setupUi()` is not covered by `retranslateUi()`, so it keeps its first language after a switch unless the code resets it.

The fl10n specification treats forms as a separate audit pass for this reason: it parses each `.ui` file, lists the translatable strings with their owning widget as context, and flags visible strings that carry `notr="true"` or are empty where a real label is expected. For Proteus, the FontLab code base it audits first, the specification counts 437 forms, which is more than anyone reviews by eye.

## Audit the source the way lupdate reads it

An instrumentation campaign on an existing code base starts with an audit, not with edits. The fl10n `scan` command reports localizability findings without changing the source, and each detector corresponds to a documented pitfall. The specification defines eleven detectors; the implementation checked for this chapter contains nine of them, and the table marks the other two.

| Detector | Finding | Severity |
|---|---|---|
| `FL-CTX-001` | `QObject` subclass with `tr()` but no `Q_OBJECT` | critical |
| `FL-TR-002` | `tr()` or `translate()` called with a non-literal | critical |
| `FL-HARD-003` | Hard-coded literal passed to a UI setter such as `setText` or `setToolTip` | major |
| `FL-NS-004` | Qualified class that `lupdate` would misfile without `-I` (specified, not yet implemented) | major |
| `FL-STATIC-005` | `tr()` at static-initialization scope | major |
| `FL-ARG-006` | Chained `.arg(a).arg(b)` | minor |
| `FL-CONCAT-007` | Concatenated translatable fragments | minor |
| `FL-NOOP-008` | `QT_TR_NOOP` outside a class (specified, not yet implemented) | minor |
| `FL-UI-009` | Visible `.ui` string not translatable | major |
| `FL-UTF8-010` | Source file not UTF-8 | info |
| `FL-TRUTF8-011` | Use of the removed `trUtf8()` | minor |

Here is the critical case as a worked example. A panel subclass omits the macro:

```cpp
class KerningPanel : public QWidget {      // no Q_OBJECT
public:
    KerningPanel() { title->setText(tr("Kerning")); }
};
```

`lupdate` files "Kerning" under the context `KerningPanel`. At run time, the inherited `tr()` asks for it under `QWidget`, finds nothing, and displays English. Recent `lupdate` versions warn that the class lacks `Q_OBJECT`, but a warning in a long build log is easy to miss. The scanner reports it as `FL-CTX-001`, and the fix is one line: add `Q_OBJECT`, or `Q_DECLARE_TR_FUNCTIONS(KerningPanel)` if the class must stay free of the meta-object system.

The scanner has two engines. The default heuristic engine uses line patterns and light brace matching; it is fast, has no dependencies and marks its results as heuristic because comments and multi-line literals can fool it. The optional Clang engine builds a real syntax tree from a compilation database, so it knows base classes and namespaces and can tell a literal from a variable with certainty; it is the engine of record for the context and literal detectors. Results come out as a table, as JSON for diffing between commits, or as SARIF for code-scanning tools. A coverage figure, marked literals divided by marked literals plus hard-coded candidates, lets a continuous-integration gate fail a change that reduces localizability, and the threshold can rise over the campaign instead of demanding full coverage on the first day. The scanner does not fix code: adding macros and wrapping literals remain reviewed human changes.

Two compiler-side guards complement the audit. Defining `QT_NO_CAST_FROM_ASCII` makes implicit conversions from `char*` literals to `QString` a compile error, which surfaces unmarked strings. And the Qt 6 migration removes the old encoding machinery: `trUtf8()` is gone, `CODECFORTR` and `QTextCodec::setCodecForTr()` no longer exist, and source files are assumed to be UTF-8. The research corpus suggests running `file -i` over the sources before the switch to find files in other encodings.

## Sources

- `research/02-localizing-qt-cpp-applications.md`, `research/06-tldr.md` and `research/01-foundations-of-software-localization.md` in the fl10n repository
- `spec/02.md`, `docs/commands/scan.md` and `src/fl10n/engines/scan.py` in the fl10n repository
- [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/) in the vexy-fontlab-writing-styleguide repository
