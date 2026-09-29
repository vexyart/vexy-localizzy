---
this_file: src_docs/md/7-process/706-pseudo-localization-and-layout.md
---

# 706. Pseudo-localization and layout testing: catching breakage before a translator sees it

The cheapest localization bug is the one found before any translator is paid. Pseudo-localization finds a whole class of them by translating the product into a language nobody speaks: every string is replaced by a longer, accented, bracketed version of itself, and the product is built and run as if that were a real locale. What survives in plain English was never extracted. What is cut off will be cut off in German. What looks odd around the brackets was assembled at runtime. Part 2 treats pseudo-localization as an engineering technique in [210. Testing world-readiness](../2-engineering/210-testing-world-readiness.md). This chapter is about where it sits in the localization process, what it may block, and what it cannot tell you.

## Why before translation

Esselink (2000) placed pseudo-translation inside internationalization testing, before the localization cycle, and again inside project evaluation: before quoting a project, a vendor should ask whether a pseudo-translation is possible, because it shows whether the files can be processed and built without corruption. His argument for doing it early is arithmetic. A defect in the source is fixed once; the same defect found after translation is fixed once per language.

Dr International (2002) gives pseudo-localization a chapter of its own and states the paradox it resolves. Localizability bugs have to be fixed in code, so they should be found early, yet they usually become visible only when a product is translated, which happens late. A pseudo-locale provides a translation "without the cost of an actual localization", early enough for developers to act. Research/04 turns this into a pipeline rule: pseudo-localize every build, before real translations exist.

The bugs it exposes, in Dr International's list, fall into a handful of kinds:

- resources the localization process never sees, because they load from a library or file outside its scope
- strings hard-coded in source or stored in a format the tools cannot open
- functional strings mixed with interface strings, such as the name of a shared object that two programs must agree on
- characters outside the source script that break storage or display
- buffers sized for English that overflow when the text grows
- strings that must be translated consistently because code compares them
- interfaces that cannot be mirrored for right-to-left languages
- sentences assembled from fragments at runtime

## Transformations and what each reveals

Pseudo-localization is not one transformation but several, and each targets a different failure. The table combines Dr International's features with the stress vectors in research/04 and the modes in the fl10n specification.

| Transformation | Example | What it reveals |
|---|---|---|
| Character replacement | *Settings* becomes *Šëţţīñğš* | Hard-coded text stays plain; encoding faults show as boxes or junk |
| Length extension | Pad by a set ratio | Truncation, overflow, fixed-width controls |
| Delimiters | Wrap each string in brackets | Where strings start and end; runtime assembly |
| Dialog stretching | Widen dialog templates | Hard-coded dialog sizes |
| Mnemonic and shortcut replacement | Swap hot-key letters | Code that depends on a particular letter |
| Pseudo-mirroring | Flip layout direction only | Interfaces that cannot be mirrored |
| Graphic and audio markers | Overlay the file name on an image | Media outside the localization scope |

The expansion ratio is where sources give numbers. Research/04 recommends lengthening strings by thirty to fifty percent and cites Microsoft guidance of about forty percent for English source text; the fl10n specification defaults to forty percent. Part 1 discusses real expansion rates in [109. Space and growth](../1-foundations/109-space-and-growth.md). For a pseudo-locale, the exact figure matters less than applying it uniformly, so that a failure points to the layout rather than to one translator's verbosity.

Delimiters deserve special attention because they reveal structure that no other check can. Dr International's worked example shows a rendered line with braces added at the start and end of each resource:

```text
{string1{string2}} string3 {string4
```

Read left to right, it says four things. The second string was inserted into the first at runtime. The third string never came from a pseudo-localized resource, so it is hard-coded or loaded from elsewhere. The fourth was truncated, because its closing brace is missing. A reviewer who sees this line has found a concatenation, a missed extraction and a layout fault without reading a word of any language.

## Preserve the syntax

A pseudo-localizer is a translation engine with no vocabulary, and it is bound by the same rules as a real one. Placeholders, markup and escapes must pass through unchanged, or the pseudo build will fail for reasons that have nothing to do with localizability. The fl10n specification says placeholders and tags are never transformed. The FontLab runtime-review guide asks for a tool that preserves message syntax, so that placeholder identifiers, markup and escapes remain functional, and warns that an unchanged user value or technical identifier may be intentional.

A small pseudo-localizer for Qt messages shows the principle. This is a sketch, not a library function:

```python
import re

ACCENTS = str.maketrans("aceinorsuyACEINORSUY", "àçéîñöřšüÿÀÇÉÎÑÖŘŠÜŸ")
PROTECTED = re.compile(r"%L?\d+|%L?n|&&|&(?=\w)|<[^>]+>")

def pseudo(text: str, expansion: float = 0.4) -> str:
    parts, last = [], 0
    for match in PROTECTED.finditer(text):
        parts.append(text[last:match.start()].translate(ACCENTS))
        parts.append(match.group())
        last = match.end()
    parts.append(text[last:].translate(ACCENTS))
    pad = "~" * max(1, round(len(text) * expansion))
    return "[" + "".join(parts) + pad + "]"

pseudo("Delete %n &glyphs")   # '[Délété %n &glÿphš~~~~~~~]'
```

The placeholder `%n` and the mnemonic marker survive; everything else is visibly foreign and longer. The same deterministic checks that guard real translations, described in chapter [704](704-the-qa-gate.md), should pass on the pseudo catalog. If they fail, the pseudo-localizer is broken, not the product.

## Where it runs, and what it may block

In the eight-stage loop of chapter [702](702-continuous-localization.md), pseudo-localization is stage 3, after the diff and before translation. The fl10n specification writes the pseudo catalog as an ordinary catalog with the target language `xx-pseudo`, converts it to `.ts` and compiles it to `.qm`, so the application loads it like any locale and the team sees overflow in the real interface. Research/04 and research/05 pair it with screenshot tests in Playwright, Cypress or Chromatic, and propose failing the build when the interface fractures.

A build failure is the right response to some pseudo findings and the wrong one to others. A string that stays in English is a missed extraction, a defect in code, and blocking is reasonable. A truncated label is a layout defect, and whether it blocks depends on what is lost, as chapter [705](705-lqa-and-mqm.md) describes. Buttons from the operating system stay in English in a pseudo build, because the system is not pseudo-localized; Dr International's pseudo-localized Notepad shows *Yes*, *No* and *Cancel* in plain English beside accented application text. Those are not defects, and a rule that fails the build on any unaccented string will fail on them.

Screenshot tests have a coverage problem that Esselink described for real translations. Dynamic dialogs show one state in a resource editor and several in the running program. His advice for linguistic testing applies to pseudo builds as well: display every dialog and menu in the running application, and generate error messages, including by typing invalid entries, so that the long and assembled messages appear. The FontLab runtime-review guide puts it more strictly: open every dialog in every state. An automated screenshot suite covers the states someone scripted.

A review tool can show layout before a build exists. The vexy-localizzy browser reviewer renders a Qt `.ui` file with the published quiht renderer and updates the preview as the reviewer types, with a Fit setting for dialogs larger than the pane. It handles standard Qt widgets and preserves their geometry; custom application widgets may appear as generic placeholders, and it does not execute application code. That makes it a quick check for label width in designer-built dialogs, not a substitute for running the product.

## Length checks, and the limits of a pseudo-locale

Not every length check needs a pseudo build. The FontLab review of September 2026 did not use one. It used a rule and a search. Issue 133 set the rule that labels in the Measurements panel should be no longer than their English originals, and the German catalog was searched for interface strings longer than the English. The FontLab guide generalizes this into a script check: flag a length ratio far outside the language's expected range, and flag any target longer than its source in a panel with a length cap. Research/04 suggests carrying such caps with the string, in an XLIFF size restriction or a JSON manifest, and asserting the length in the gate.

A length rule is cheap and exact, and it catches the panel you already know is tight. A pseudo build catches the panels you did not know about. The FontLab audit states the limit of the first approach in its own words: its checks do not establish pixel fit in the interface. Characters are not pixels, and the widest German word in a proportional font is a matter for the running product.

What a pseudo-locale cannot tell you is just as clear. The FontLab runtime-review guide draws the boundary: pseudo-localization does not establish natural wording, correct agreement or approved terminology. It proves that the product can carry a translation. It says nothing about whether any particular translation is right. Dr International adds the other half: a pseudo-localized product that passes still needs functional testing once it is really localized, only less of it.

Keep the failures pseudo-localization finds, and rerun their cases after each repair. A missed extraction fixed once can return with the next feature, and the pseudo build is the cheapest place to see it come back.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 5: internationalization testing and pseudo-translation, linguistic testing of dynamic dialogs; chapter 13: pseudo-translation in project evaluation)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 11: localizability testing; chapter 12: pseudo-localization)
- `research/04-ai-driven-translation-and-quality-assurance.md` in the fl10n repository (sections 4.7.1 and 4.7.2)
- `research/05-format-conversion-cicd-and-continuous-localization.md` in the fl10n repository (section 5.4.2)
- `spec/05.md` in the fl10n repository (section 5.2)
- [docs/review.md](../8-toolkit/review.md) in the vexy-localizzy repository
- [localization/runtime-review](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/runtime-review/) and [localization/quality](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/quality/) in the vexy-fontlab-writing-styleguide repository
- `data-fontlab-cpp/i18n/review/README.md` in the fl10n repository (issue 133 and audit limits)
