---
this_file: src_docs/md/6-machine-translation/603-context-engineering.md
---

# 603. Context engineering: what a model needs to translate a label correctly

A translator who receives the English word "Close" asks what it closes. A model does not ask. It chooses the most probable reading and writes a fluent answer. The FontLab writing guide gives the case that matters: *Close* on a button and *Close* as the state of a path are different words in German. Nothing in the five letters tells them apart.

Context engineering is the name the 2026 research corpus gives to the work of deciding what information travels with each string, assembling it reliably, and presenting it so the model uses it. This chapter lists what to send, shows how to structure the request, and explains where context runs out.

## Why a label is ambiguous

Interface strings are short, and short strings are ambiguous in ways a sentence is not. A label may be a verb or a noun ("Open", "Book", "Kern"), a command or a state ("Close", "Locked"), a product feature or an ordinary word ("Smart", "Flex"), and it may be compressed in a way the translation should copy ("If mask is active"). Part 5 treats each of these as a translation problem; here they are a data problem. The information that resolves them exists somewhere: in the source code, in the developer's head, in the dialog the string sits in. It has to be carried to the model.

Roturier (2015) lists why developers often fail to supply it. They expect the translator to know the product, they are reluctant to show an unreleased application even under a non-disclosure agreement, or they judge the extra work unnecessary. The result, he notes, is mistranslated ambiguous strings and truncated labels that a quality assurance pass must catch later, when they could have been avoided by preparing the source. Machine translation removes the one safeguard that used to catch the problem early: the translator's question.

## The context bundle

The research corpus aggregates the fields that repay the effort. The fl10n specification maps them onto a catalog. The table below combines both, with the Qt field that usually carries each one.

| Field | What it resolves | Where it comes from in a Qt project |
|---|---|---|
| Source string and target locale | the task itself | `<source>`, the catalog's `language` |
| Context or key | module and intent | `<context><name>`, usually the class name |
| Disambiguation and developer comment | verb or noun, what a placeholder holds | `tr()` disambiguation, `//:` comments, `<comment>`, `<extracomment>` |
| UI element type | button, menu item, tooltip, title | inferred from context and comment, or declared |
| Length budget | overflow | a declared maximum or length variants |
| Placeholder and markup inventory | what must survive unchanged | parsed from the source (see [606](606-the-placeholder-protocol.md)) |
| Sibling strings | register and terminology within one screen | other messages in the same context |
| Glossary hits | approved renderings of product terms | the core memory (see [605](605-glossary-enforcement.md)) |
| Style guidance | register, headline compression, typography | the language's style sheet |
| Memory examples | how similar strings were translated before | project memory, retrieved examples with provenance |
| Screenshot | layout, neighbours, visible space | captured from the running build |

The research corpus reports that hierarchical keys such as `export_dialog.format_selector.label`, compared with flat keys such as `label_03`, are the change with the highest return for AI translation quality without touching the model or the prompt. Qt projects rarely have such keys. Their equivalent is a meaningful context name plus a disambiguation string and a comment, which is why [205](../2-engineering/205-qt-instrumentation.md) spends so long on `tr()` comments. A comment written for a human translator is read by the model too.

The screenshot is the richest field and the hardest to supply. The research corpus reports teams reaching first-pass approval rates above 70 percent when visual context accompanies short strings, and one case of 71 percent perfect Japanese UI translations; both figures come from vendors and deserve the caution [608](608-quality-estimation-and-judges.md) applies to vendor numbers. The corpus names the strings that gain most from a screenshot: the short, context-dependent ones such as "OK", "Cancel", "Done" and "Book", where the image shows whether a word is a verb on a button or a noun in a list.

Commercial platforms have started to harvest this context automatically. The research corpus reports that Crowdin's command-line tool can pull code comments, component names and file paths into generated context, and that Weblate forwards the message context, the key, the explanation, translations into secondary languages, plural information, failing quality checks and placeholder contents to its model, a capability the corpus dates to Weblate 5.3. A team building its own pipeline should aim for the same list, gathered by the extraction step rather than typed by hand.

## Structuring the request

A request that mixes rules, context and strings in one paragraph invites the model to treat a rule as content. The research corpus and the fl10n specification separate four concerns: the policy (the invariants that must hold), the context (the bundle above), the payload (the strings), and the output contract (the exact shape of the answer). The behavioral instruction is "respect invariants", not "be creative": placeholders, tags, accelerators and approved terms are fixed, and terminology and interface tone outrank literal wording.

The corpus's own FontLab example, written as a JSON payload, shows two strings with their context and typed variables:

```json
{
  "project_context": {
    "app_name": "FontLab",
    "domain": "Typography and Font Engineering"
  },
  "translation_payload": [
    {
      "key": "mainWindow.menu.file.open",
      "source_string": "Open",
      "context": "Verb. Menu action to open a font file.",
      "max_characters": 15,
      "variables": {}
    },
    {
      "key": "dialog.metrics.kerning.pairsFound",
      "source_string": "Found %1 kerning pair(s) in %2.",
      "context": "Status message displaying search results. %1 is the count of pairs, %2 is the font master name.",
      "max_characters": 80,
      "variables": { "%1": "integer", "%2": "string" }
    }
  ]
}
```

The output contract asks for JSON keyed by message, so the pipeline can check that every message came back exactly once. vexy-localizzy's transport checks exact coverage of message IDs, duplicate fields and empty targets before anything else looks at the text. A contract that also asks for the tokens the model believes it preserved, a confidence and a list of issues, as the fl10n specification proposes, gives the validator something to compare, though a model's report of its own confidence is a hint, not a measurement.

The specification also groups strings by context, roughly one dialog or screen per request, so the model sees siblings and keeps terminology consistent within a screen. [607](607-routing-batching-and-cost.md) returns to batch size.

Context resolves more than word sense. In the FontLab German review (issue 133), the founder rejected *Wenn die Maskenebene aktiv ist* for the preferences label "If mask is active" and asked for *Wenn Maske aktiv*: no article, no verb, and *Maske* rather than *Maskenebene*, although a mask is a layer in FontLab. The draft was grammatical and accurate. It was wrong because it ignored two facts that no single string reveals: that the English is written in a compressed headline style for a confined space, and that the house rule is to carry that compression into the translation and never to add detail the source omits. Both facts belong in the bundle. The first comes from the element type and length budget, the second from the style sheet. A model that receives them can produce the compact form on the first pass. A model that receives only the string will tend to produce the careful sentence that a reviewer then shortens by hand, one label at a time.

## What the FontLab Polish catalog sent

The first Polish catalog, 10,474 messages when it was produced in September 2026, shows what a working bundle looked like. The model was claude-opus-5-5, driven by `fl10n localize` through vexy-localizzy. Each request carried:

- the messages of whole Qt contexts, because the catalog was split into four shards that kept every context intact;
- each message's context and comment;
- the terms from the Polish core memory that occurred in the batch;
- the matching entries of an attested seed glossary, 148 interface concepts and 460 short interface strings taken from FontForge, Scribus, InDesign and the Polish editions of Bringhurst and Felici;
- a Polish style sheet with the language's rules. The writing guide's recorded decisions for Polish include *matryca* for master, *sprytny* for smart, and the feature names that stay English.

The command has no screenshot input, so the requests carried none. The draft passed the placeholder, markup, accelerator and three-form plural checks and compiled fully finished. It still contained renderings the founder replaced a day later, such as *reguła przetwarzania OpenType* for lookup, now *podprogram zecerski*. Context engineering cannot supply a decision nobody has made yet. That is the job of terminology work in Part 4.

## Where context runs out

Context has three limits worth knowing before building a pipeline around it.

First, context is only as good as the source. A comment that is wrong or stale misleads the model with confidence. [508](../5-interface/508-source-text-as-evidence.md) covers source defects; a model will not flag one unless asked.

Second, more is not always better. The FontLab guide warns that a glossary of two hundred terms attached to a ten-string batch drowns the terms that matter, and the same holds for pasted style guides and long example lists. Send what applies to the strings in the request.

Third, context costs confidentiality. Every field in the bundle is information about an unreleased product, and a screenshot is the most revealing of all. [610](610-data-terms-and-trust.md) treats the provider question; here it is enough to note that the tension Roturier described for human translators in 2015 applies with more force when the recipient is a service.

A model can also help with context rather than receive it. The FontLab guide lists asking a model what a short string most likely labels as a sound use, provided a person decides. That turns the missing translator's question into a step the pipeline can perform on purpose.

## Sources

- Johann Roturier, *Localizing Apps: A Practical Guide for Translators and Translation Students*, 2015 (section 3.2.4: comments, context and confidentiality)
- `research/04-ai-driven-translation-and-quality-assurance.md` in the fl10n repository (sections 4.2 to 4.4)
- `research-draft/203-ai-localization-automation.md` in the fl10n repository (context-aware prompting)
- `spec/04.md` in the fl10n repository (sections 4.2 and 4.3)
- `issues/133.md` in the fl10n repository (the founder's German review remarks)
- `WORK.md` and `CHANGELOG.md` in the fl10n repository (issue 145: the Polish catalog)
- `scripts/shard_ts.py` in the fl10n repository
- [docs/translation.md](../8-toolkit/translation.md) in the vexy-localizzy repository
- [localization/memories](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/memories/), [localization/message-contracts](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/message-contracts/) and [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
