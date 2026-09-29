---
this_file: src_docs/md/2-engineering/207-web-and-typescript.md
---

# 207. Web and TypeScript: Intl, i18next, FormatJS, Lingui and typed keys

A web application meets the same problems as a desktop one, with three differences. The formatting engine is built into the platform, as the `Intl` API. The catalogs travel over the network, so their size and loading order matter to every user. And the choice of library is wide, with benchmarks that disagree. This chapter explains the decisions in the order a team faces them: what to leave to `Intl`, which message model to adopt, how to make TypeScript catch missing keys, and how to deliver the right catalog to the right request.

## Let the platform format

The ECMAScript `Intl` namespace formats numbers, dates, relative times, lists and names, selects plural categories, compares strings and segments text, all from locale data that ships with the browser or the JavaScript runtime. Every serious library delegates to it. The research corpus puts the rule plainly: rely on native `Intl`, never ship a custom formatter, and add a polyfill only for the newest constructors on old browsers.

| Constructor | Purpose |
|---|---|
| `Intl.NumberFormat` | Numbers, currency, percentages, compact notation |
| `Intl.DateTimeFormat` | Dates and times, with time zones |
| `Intl.RelativeTimeFormat` | "3 minutes ago", "tomorrow" |
| `Intl.PluralRules` | The plural or ordinal category for a number |
| `Intl.Collator` | Locale-aware comparison and sorting |
| `Intl.ListFormat` | "A, B and C" |
| `Intl.DisplayNames` | Names of languages, regions and currencies |
| `Intl.Segmenter` | Grapheme, word and sentence boundaries |

```ts
const amount = 1250000.75;
new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(amount);
// "1.250.000,75 €"
new Intl.PluralRules('pl').resolvedOptions().pluralCategories;
// the categories a Polish message must provide
```

Two habits keep `Intl` honest. Store amounts with their currency code and format them at display time; a price stored as a formatted string cannot be reformatted and invites the mistake of converting the display without converting the value ([106](../1-foundations/106-numbers-dates-and-units.md)). And never write plural rules by hand. Baldurs (2025) shows why in the course of teaching `Intl.PluralRules`: its own hand-written tables give English a `zero` category, although CLDR gives English only `one` and `other`, and reduce Polish to one for 1, few for 2 to 4 and many from 5 upward, which is wrong for 22 to 24, 32 to 34 and so on, and for every fraction. `Intl.PluralRules` has none of these mistakes.

## Choose a message model

Web i18n libraries divide along two lines. Runtime libraries resolve messages in the browser and ship a parser; compile-time libraries extract and compile catalogs at build time, so the parser and unused messages disappear from the bundle. Independently, some libraries use their own JSON conventions and others embed ICU MessageFormat in the string. The research corpus concludes that architecture matters more than the brand: message precompilation, lazy loading of locales and correct server rendering move performance more than the choice between libraries.

| Library | Model | Message syntax | Notes from the research corpus |
|---|---|---|---|
| i18next, react-i18next | Runtime | Own JSON; ICU through a plugin | Largest plugin set; `{{name}}` interpolation, escaped by default |
| FormatJS, react-intl | Runtime, optional precompilation | ICU MessageFormat | Descriptor model: `id`, `defaultMessage`, `description` |
| Lingui | Compile time | ICU, compiled to functions | PO catalogs by default; macros extract natural text |
| next-intl | Runtime, server-first | ICU | Translations rendered on the server add no client JavaScript |
| vue-i18n | Both | Own syntax; ICU experimental | Version 11 completed the move to the Composition API |
| Paraglide JS | Compile time | ICU through a plugin | Each message is a typed, tree-shaken function |
| Fluent | Runtime | Fluent (FTL), not ICU | Translators control grammatical branching |

The bundle sizes the sources report disagree, sometimes by a factor of two for the same library, because they were measured at different dates, with different tools, and with or without the framework bindings. For react-i18next the corpus cites about 18.5 kB compressed in one source, about 22 kB as the sum of core and binding in another, and 23.1 kB minified or 9.2 kB compressed in a third. The consistent finding is the ranking: i18next and react-intl are heavy, at roughly 15 to 25 kB; Lingui, Paraglide and micro-libraries are light, at roughly 1 to 8 kB. Measure your own build before choosing on size.

Here is the same message in the two dominant models, for a Polish target. Polish needs four plural categories: `one`, `few`, `many` and `other`, the last used for fractions ([505](../5-interface/505-plurals-in-practice.md)).

```json
{
  "files_one": "{{count}} plik",
  "files_few": "{{count}} pliki",
  "files_many": "{{count}} plików",
  "files_other": "{{count}} pliku"
}
```

```json
{
  "files": "{count, plural, one {# plik} few {# pliki} many {# plików} other {# pliku}}"
}
```

i18next spreads the forms over sibling keys named with CLDR category suffixes; ICU keeps them in one string that the translator edits as a unit. The ICU form is portable across libraries and platforms and keeps agreement decisions together; the i18next form is easier for simple tools to diff. For gender and other selections, ICU uses `select`, which the research corpus recommends placing outside `plural` at the top of the message, with whole sentences in each branch.

Unicode MessageFormat 2 is specified but barely used in production. The corpus reports six weekly downloads for the i18next MF2 adapter against about 355,000 for the `messageformat` package, and the TC39 `Intl.MessageFormat` proposal held at Stage 2.7. `Intl.MessageFormat` is therefore a proposal, not an API you can call today, whatever some examples suggest. The corpus recommends authoring in ICU MessageFormat 1 through at least 2026 and keeping storage format-agnostic.

## Make TypeScript check the keys

In a typed code base, a call with a key that does not exist should fail the build rather than display the key to a user. Libraries that keep messages in JSON get this from a declaration that maps namespaces to the English resource files. For i18next, the pattern the research corpus and Baldurs both describe augments `CustomTypeOptions`:

```ts
// i18next.d.ts
import 'i18next';

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: {
      common: typeof import('../locales/en/common.json');
      errors: typeof import('../locales/en/errors.json');
    };
  }
}
```

With that in place, and a `save` key in the English `common.json`, `t('common:save')` compiles and the misspelled `t('common:sav')` does not. The English files are the source of truth for the types, and other languages are checked against them by tooling. next-intl uses the same idea with its `IntlMessages` interface. Compile-time libraries such as Paraglide go further: each message is a generated function, so a missing message or a missing argument is a type error by construction.

Three limits apply. Keys built at run time, such as `` t(`categories.${id}`) ``, defeat both type checking and extraction; list the possible keys explicitly. In a monorepo, hoisted dependencies can resolve two versions of a library and silently lose the augmentation; the corpus suggests project references or package-manager overrides. And type checks establish only that a key exists. The FontLab writing guide states the boundary: typed keys can catch some mistakes during development, but they cannot approve a translation or prove that a catalog reaches the released application, and a test that asserts only that `t()` returned a string passes for an untranslated key.

## Deliver the right catalog to the right request

Shipping every language in the main bundle makes every user download text they cannot read. Load catalogs per locale and per namespace instead, from dynamic imports or an HTTP backend, and cache them with content-addressed file names. One trap is documented in the corpus: a fully dynamic import expression can make the bundler include every locale chunk anyway, so name the locales explicitly.

Server rendering adds two rules. Keep the i18n instance and the active language scoped to the request: the corpus documents a Nuxt case in which a module-level instance let one user receive another user's language when requests overlapped. And pass pre-translated strings to client components rather than whole dictionaries or the translation function, which bloats the serialized payload and slows hydration.

For locale detection, the corpus reports a precedence that most frameworks converge on: a locale segment in the URL, then a saved cookie, then the `Accept-Language` header matched against supported locales, then the default. A path segment such as `/de/` keeps pages cacheable and indexable; a cookie-only strategy forces dynamic rendering. When the language changes, set `lang` and `dir` on the root element, as Baldurs shows, so that fonts, hyphenation and direction follow ([208](208-mirroring-and-rtl.md)).

The language selector itself is where the sources disagree most visibly. Roturier (2015), following W3C advice, recommends listing each language by its own name, avoiding flags because a language is not a country, and treating IP-based location as unreliable; he suggests a globe icon for the selector. Baldurs builds a selector with flag emoji and devotes a section to choosing the language by IP geolocation. Roturier's position is the one this book recommends: a country tells you little about the language a person reads, and the FontLab runtime review adds that browser preferences can suggest an initial language but do not establish currency, address or time zone.

Rich text follows the placeholder rule of [204](204-placeholders-and-grammar.md). Store `"I agree to the <1>Terms</1>."` and let the component supply the link, as react-i18next's `<Trans>` does, rather than storing raw HTML and injecting it; i18next escapes interpolated values by default, and turning escaping off moves that duty to you.

On the file side, Localizzy converts between i18next JSON, its canonical JSON and the other catalog formats with `localizzy convert`, and its extraction of keyed JSON resources joins source and target strictly by typed path, never by position ([305](../3-formats/305-json-android-apple.md)).

## Sources

- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025 (chapters 2 to 4, 6, 9 and 15)
- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (chapter 3, the global gateway)
- `research/01-foundations-of-software-localization.md`, `research/03-localizing-web-javascript-applications.md` and `research/06-tldr.md` in the fl10n repository
- [localization/message-contracts](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/message-contracts/) and [localization/runtime-review](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/runtime-review/) in the vexy-fontlab-writing-styleguide repository
- `README.md` and [docs/extraction.md](../8-toolkit/extraction.md) in the vexy-localizzy repository
