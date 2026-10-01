---
this_file: src_docs/md/2-engineering/index.md
---

# Part 2. Internationalization engineering

A translation that exists but never reaches the screen is an engineering defect, and so is a sentence that no translator can make grammatical. This part is about the work that prevents both: designing a program so that its text and its cultural assumptions live in data rather than code, externalizing strings with enough context to translate them, handling values inside messages without breaking grammar, instrumenting Qt and web code, loading and switching languages at run time, mirroring layouts for right-to-left languages, rendering complex scripts, and testing all of it before a single real translation arrives. It condenses thirty years of practice, from X/Open message catalogs and Win32 resource files to Qt 6 and TypeScript, and uses the FontLab applications and the Localizzy toolkit as worked examples where they help.

- [201. What this part knows](201-what-this-part-knows.md)
- [202. World-ready design: separating code from text, data from presentation](202-world-ready-design.md)
- [203. Externalizing strings: keys, contexts, comments and the message-key model](203-externalizing-strings.md)
- [204. Placeholders and grammar: variables, ordering, agreement and the no-concatenation rule](204-placeholders-and-grammar.md)
- [205. Qt instrumentation: tr(), contexts, disambiguation, NOOP macros and .ui files](205-qt-instrumentation.md)
- [206. The Qt toolchain and runtime: lupdate, lrelease, lconvert, QTranslator, language switching](206-qt-toolchain-and-runtime.md)
- [207. Web and TypeScript: Intl, i18next, FormatJS, Lingui and typed keys](207-web-and-typescript.md)
- [208. Mirroring and right-to-left interfaces: layout, icons and mixed direction](208-mirroring-and-rtl.md)
- [209. Rendering text: OpenType features, fallback fonts and complex scripts](209-rendering-and-opentype.md)
- [210. Testing world-readiness: pseudo-localization, locale switching and mixed data](210-testing-world-readiness.md)
