---
this_file: src_docs/md/8-toolkit/pseudo.md
---
# Pseudo-localization

A pseudo-locale is the cheapest test a localization project has. It needs no
translator and no model, and it shows in the running application what will
break: text that stays plain was never extracted, text cut off at the end has
no room to grow, and text with a bracket missing in the middle was built by
concatenation.

```sh
localizzy pseudo i18n/fresh/app_en.ts i18n/app_xx.ts
localizzy pseudo i18n/fresh/app_en.ts i18n/app_xx.ts --mode bracket --expansion 0.3
localizzy pseudo catalog.json pseudo.json --mode rtl
localizzy qt release i18n/app_xx.ts
```

The output format follows the suffix of OUT: `.ts`, `.json`, `.po`, `.xlf` or
`.xliff`, `.xml` for Android. The target language becomes `xx-pseudo`, every
active message is filled and marked finished, and vanished messages are left
alone. Plural forms and length variants all receive the pseudo text, so a
compiled catalog shows something in every slot. A conversion that would lose
data stops with exit 2 unless `--allow-loss` is given, and so does an OUT
that is the input catalog.

## Modes

| Mode | `Open Font` becomes |
|---|---|
| `accent` (default) | `⟦Óρēņ Fōņţēēē⟧` |
| `bracket` | `[Óρēņ Fōņţ ēēē]` |
| `rtl` | `Open Font` between U+202B and U+202C |

`accent` replaces ASCII letters with accented and look-alike letters, pads the
text with `ē` by `--expansion` of its plain length (default 0.4, at least one
character) and wraps it in `⟦ ⟧`. `bracket` does the same with plain square
brackets and a space before the padding, for fonts that lack the white
brackets. `rtl` leaves the text unchanged inside a right-to-left embedding
(U+202B) and its terminator (U+202C), to show which layouts do not mirror;
it ignores `--expansion`.

Forty per cent is a deliberate margin. German UI text commonly runs a fifth to
a third longer than English, and short labels grow by far more than long
sentences.

## What is never changed

Only plain runs of text are transformed. These survive verbatim, so the
pseudo catalog passes the same placeholder checks as a real one:

- Qt arguments: `%1`, `%L1`, `%n`, `%Ln`;
- printf conversions with their flags, widths, precisions and length
  modifiers: `%s`, `%u`, `%ld`, `%.2f`, `%-5s`, `%1$s`, `%(name)s`, `%%`;
- brace placeholders: `{0}`, `{name}`, `{{count}}`;
- the skeleton of ICU plural and select blocks: the argument name, the
  keyword, the selectors, `#` and nested placeholders. The text of each arm is
  transformed, so `{count, plural, one {# glyph} other {# glyphs}}` keeps
  its structure and shows pseudo text in both arms;
- markup tags and character entities: `<b>`, `&amp;`, `&#169;`;
- accelerators and literal ampersands: `&Open`, `&&`.

Pseudo-localization checks layout and extraction, not language. It does not
replace a look at the real translation in the running application.
