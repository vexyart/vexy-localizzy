---
this_file: src_docs/md/1-foundations/110-culture-and-cost.md
---

# 110. Culture, law and cost: what to adapt, what to leave, and what it costs

The previous chapters dealt with conventions that locale data can settle: how to write a date, which plural form to use, where a line breaks. This chapter deals with the decisions no database settles. Which images, examples and names should change for a market? Which legal requirements apply? And how much of this is worth paying for? These decisions sit with the people who own the product and the budget, not with the translator, but a translator is often the first to notice that one is needed. The chapter gives both sides a common frame.

## Culture: the visible layer and the rest

Jiménez-Crespo (2024) traces how the industry's idea of culture widened. In early software localization, cultural adaptation meant technical conventions: numbers, names, dates, currency, measurements, sort orders and keyboard mappings, the subjects of chapters [104](104-characters-and-encodings.md) to [108](108-scripts-direction-and-fonts.md). As content types multiplied, it came to include how users interact with a shop, how game characters are drawn and what a product assumes about its user.

Jiménez-Crespo uses Hall's image of culture as an iceberg to explain why adaptation work tends to stop too early. The visible level holds music, food, dress and visible behavior. Below it lies the formal level of customs and what counts as appropriate. Deepest is the level people are not aware of: attitudes to time, power, space and the individual. Localization, the book observes, usually addresses the visible level (keyboards, colors, photos, measurements) and rarely mentions the rest. Hall's related distinction between low-context and high-context cultures shows what that costs: explicit warnings typical of low-context writing, such as a note that a product will be hot after microwaving, can read as condescending in a high-context culture.

For software, the scholar Tercedor, as Jiménez-Crespo reports, identified the levels open to adaptation:

| Level | Examples in an application |
|---|---|
| Linguistic and textual | How the user is addressed, register, references to songs or books, the structure of a legal text |
| Visual and iconic | Icons, photographs, colors, pictograms |
| Technical | Keyboard layouts, scripts, measurement, paper sizes: the content of locale data |
| Cognitive | Navigation, metaphors, mental models, interaction |

The icon row has the best-known failures. Jiménez-Crespo cites the *My Briefcase* icon of early Windows, whose purpose users did not understand, and the house icon for a browser's *Home* command, which Spanish localizes as *Página principal* (start page) and French as *Accueil* (welcome). An icon is a word nobody can translate.

What is the aim? Jiménez-Crespo is explicit that cultural adaptation is not meant to persuade users that a product was made locally. It is meant to show that the company is aware of the receiving culture and respects it. That aim also tells you what to leave alone: the product's own names, its identity and the parts of its voice that users of every language share. The FontLab principles in the writing styleguide show the balance at the level of a single word. The feature family called *Smart* is translated with the sense of *clever*, with a hint of cunning (German *schlau*, Polish *sprytny*), and never as *intelligent*, which in 2026 reads as a claim about artificial intelligence. Names such as Genius, Fusion and Flex stay in English where the language has no equivalent for exactly that thing.

## Images, examples and media

Roturier (2015) lists the non-textual content that may need adaptation and the traps in each kind.

- **Screenshots** in help and store listings. Roturier notes that English screenshots in a French or German app store listing can hurt uptake in those locales. A localized screenshot needs a localized build, and for store pages it also needs representative data typed in the target language.
- **Text inside graphics.** Editing it needs image software and time, which is why the older literature urges keeping text out of images; Esselink (2000) observes that layered source files with the text on its own layer save a great deal of cost.
- **Maps and flags.** Borders are not recognized the same way everywhere, and Roturier warns that a fixed representation of the world can lead to an application's rejection.
- **Video.** A tutorial that shows the interface cannot be localized by subtitles alone when the viewer must find labels on screen. Roturier suggests that recording the video again, in the target language with the localized interface, may be the only satisfactory route. Subtitles have their own limit: Roturier cites a guideline of no more than 12 characters per second.

Examples and sample data belong here too. A tutorial whose sample names, addresses and currencies come from one country is a small cultural claim on every page.

## Law and regulation

Some adaptation is not optional. The sources give examples from four decades.

- **Language requirements.** Esselink (2000) reports that local law often requires imported hardware or devices to come with a manual in the local language, and that some countries, Baltic states among them, restricted importing or using products that were not in the national language. O'Donnell (1994) notes the same requirement for documentation, and that Spain required computer keyboards to have a key for *ñ*.
- **Rules built into the product.** Uren, Howard and Perinotti (1993) point out that an accounting application that computes depreciation by one country's rules is inappropriate elsewhere "no matter how well the Localization is executed". Medicine, insurance and law are similar. That is a product change, not a translation.
- **Legal text.** Roturier (2015) notes that some parts of a localized product may have to be written from scratch to meet local law, such as an end-user licence agreement. Jiménez-Crespo (2024) adds that the structure of legal terms varies by locale.
- **Content restrictions.** Games have been banned or given higher age ratings over religion, history or geopolitics, with consequences for sales and for a company's relations with the local government (Jiménez-Crespo, 2024).

The practical rule is organizational. Legal adaptation is decided by someone accountable for it, recorded as a requirement, and handed to translators as source text. A translator who silently "localizes" a licence clause has changed a contract.

## Cost

Localization has always been priced by units of work, and Esselink's (2000) description of a quotation is still the best map of where the money goes:

| Item | How it was charged in 2000 | Note |
|---|---|---|
| Software translation | per source word | usually 20 to 30% above the documentation rate, sometimes double when resizing and linguistic testing are included |
| Help and documentation translation | per source word | reduced by translation memory matches |
| Terminology research | per hour or per term | |
| Engineering | per dialog box or per hour | resizing, hot keys, compiling |
| Testing | per hour or per help topic | |
| Desktop publishing and graphics | per page, per screen or per hour | |
| Project management | 10 to 15% of the total | plus 2 to 5% for communication at some vendors |

Two of Esselink's notes still matter. Volumes should be analysed against existing memories as new, changed and unchanged words, because reuse drives the price. And localization usually counts source words, while in some countries translators charged per target line of about 55 characters, so quotations from different traditions do not compare directly.

The largest cost is set before any of these lines: how well the product was internationalized. Uren, Howard and Perinotti (1993) described retrofitting as repeating every step for every language. Dr International (2002) argued that delaying international work is expensive. Baldurs (2025) puts numbers on the difference and attributes them to LISA research:

| When internationalization happens | Cost, as a share of the original development budget |
|---|---|
| During initial development | about 15 to 25% |
| Retrofitted into an existing application | 50 to 100% |

The book gives no citation for the figures, so treat them as an order of magnitude, but the direction agrees with the older books.

The 2026 research corpus describes a different cost structure. Machine drafts cost little per word, so the budget moves to context preparation, automated checks and the human review of the strings that need judgment. Its recommendations include three thresholds:

| Signal | Threshold | Action |
|---|---|---|
| Model spend as a share of localization spend | above about 30% | re-architect the pipeline |
| Human approval rate of a model's drafts for one language | below about 70% | rotate the model out |
| A language's share of revenue | above 5% | never ship machine pre-translations without human review |

Its subscription prices for translation management systems are dated to 2025 and 2026 and marked "verify current"; any figure of that kind will be stale by the time you read it. vexy-localizzy's own design reflects the same economics: it fills a catalog from kept translations and memories before it asks a model, so that only new text reaches the engine (Part [6](../6-machine-translation/604-memory-first-pipelines.md)).

## A worked example: planning a Polish release

A team plans a Polish release of a font editor whose content, as recorded for the FontLab Polish draft in the writing styleguide, comprises an interface catalog of 10,474 messages, 115 Help Panel articles and 51 welcome tips. For each item the team decides one of three things, using the levels of localization from chapter [102](102-what-localization-is.md).

1. **Translate.** The interface catalog and the Help Panel. The cost drivers are terminology and review, not typing: the Polish guide lists dozens of term decisions, from *matryca* for a master to *firet* for the em, many of them checked against published Polish usage and some still waiting for attestation.
2. **Adapt.** Screenshots in the help, rebuilt from the Polish build; the tips that refer to examples, whose sample text should show Polish diacritics; and any store page, where Roturier's warning about English screenshots applies. Feature names follow the principles page: translated where Polish has an established equivalent (*Smart* as *sprytny*), kept where it does not (Genius, Fusion).
3. **Leave.** OpenType feature tags, glyph names, file names, Python identifiers and every other literal the interface-strings guide protects, plus the legal texts unless counsel supplies a Polish version.

Then add up the work, not the words: the review hours for terminology, the engineering to rebuild screenshots, and the runtime review of every dialog. The sum is the cost of a Polish edition users will trust. Parts [4](../4-terminology/401-what-this-part-knows.md) and [7](../7-process/708-vendors-tms-and-projects.md) take the terminology and the project management further.

## Sources

- Emmanuel Uren, Robert Howard and Tiziana Perinotti, *Software Internationalization and Localization: An Introduction*, 1993 (chapter 1: retrofitting, applications bound to national rules)
- Sandra Martin O'Donnell, *Programming for the World*, 1994 (chapter 1: legal requirements)
- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 1: legal requirements; chapter 14: project evaluation, pricing and cost breakdown)
- Microsoft Corporation (Dr International), *Developing International Software*, second edition, 2002 (chapter 1: the cost of delaying international editions)
- Johann Roturier, *Localizing Apps*, 2015 (section 1.3; chapter 6: adaptation of non-textual content)
- Miguel A. Jiménez-Crespo, *Localization in Translation*, 2024 (chapter 5: culture in localization)
- Baldurs L., *TypeScript Internationalization (i18n) and Localization (L10n)*, 2025 (chapter 1: the hidden costs of retrofitting)
- `research/05-format-conversion-cicd-and-continuous-localization.md` in the fl10n repository (sections 5.5 and 5.6)
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/ui-strings](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/ui-strings/) and [localization/pl](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/pl/) in the vexy-fontlab-writing-styleguide repository
- `README.md` in the vexy-localizzy repository
