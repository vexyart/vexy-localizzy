---
this_file: src_docs/md/4-terminology/407-house-voice-across-languages.md
---

# 407. House voice across languages: humor, Power names, Smart features, down-to-earth terms

Most terminology guidance is about precision, and most of this part is too. But a product's terms also have a tone. FontLab calls a mode that drags neighbouring nodes along *Power Nudge*, a tool that reconciles masters *Matchmaker*, and a preview that shows the glyph filled black *True Fill*. Those names were chosen to sound like something: energetic, friendly, a little cheeky. A translation that renders them with the most neutral technical phrase available is accurate and loses the voice.

This chapter collects the rules the FontLab founder set for carrying that voice into other languages, in issues 133, 146 and 147, and shows how each played out in German, Spanish, French and Polish. The rules are specific to one house, but the method is general: decide what kind of word the source chose, and choose the same kind of word in the target.

## Humor and wordplay are allowed

The first rule is permission. Terms may be funny, and a funny term is often a better term, because it is easier to remember and easier to say. The Polish decisions of issue 146 are full of examples:

- **Matchmaker** became *swat*, the traditional village matchmaker who arranges marriages. The tool matches masters so they can interpolate; the Polish word keeps the image and loses the English.
- **True Fill** became *Pełna krasa*, from the idiom *w pełnej krasie*, "in all its glory". The earlier *Prawdziwe wypełnienie*, "true filling", was a literal translation that said nothing a user could picture.
- **Dream Up**, a generation feature, became *wyczaruj*, "conjure it up".

The core memory note on *Pełna krasa* adds an invitation: it is a concise idiom, and similar solutions are worth finding in other languages. At the time of writing, German, Spanish and French still render True Fill literally, as *Echte Füllung*, *Relleno real* and *Remplissage réel*, and keep *Dream Up* in English. The later German review names Matchmaker **Synchronsprecher**, a dubbing actor: it builds the joke around *synchron* and matching masters. Spanish and French still keep *Matchmaker* in this comparison. Those are not errors; they are the obvious places where a native reviewer with a good idiom could improve the product.

Humor has one condition, stated in the house writing rules: the information must remain true when the joke is missed. A user who does not catch the idiom in *Pełna krasa* still reads "full", which is what the preview shows. A user who does not know the word *swat* still sees it on a tool with a tooltip. A joke that becomes a riddle fails the condition.

## Power names are playful power

FontLab has a family of *Power* features: Power Brush, Power Guide, Power Stroke, Power Nudge. The founder's instruction in issue 147 is to translate *Power* a little jokingly, with the kind of words used in energy drink advertising or for superheroes: "Not serious power, more power like in Power Rangers." The Polish names follow it:

| English | Polish | Literal sense |
|---|---|---|
| Power Brush | *Pędzel mocy* | brush of power |
| Power Guide | *Prowadnica mocy* | guide rail of power |
| Power Stroke | *Obrys mocy* | stroke of power |
| Power Nudge | *superholowanie* | super-towing |

*Moc* is the power of a hero's weapon or a magic item, not the power of an engine rating, and the phrasing *X mocy* sounds like equipment in a game. Power Nudge takes a different route, the prefix *super-*, presumably because a two-word *holowanie mocy* would be longer and heavier than the one-word prefix form; the memory note does not say.

The other languages chose differently, and the difference is instructive. German builds hyphenated compounds with the English word: *Power-Pinsel*, *Power-Hilfslinie*, *Power-Strich* and, after issue 133, *Power-Schub* for Power Nudge, a punchy word where the draft had *Verschieben*. French keeps *Power Brush* and *Power Stroke* in English and writes *guide Power*. Spanish keeps *Power* as a name, *pincel Power* and *guía Power*, and its guide records why *potente* was rejected: it suggests a value judgment and explains nothing about the feature. Spanish and French render Power Nudge as *Empuje fuerte* and *poussée forte*, a strong push. All of these avoid the serious reading of *power*. Only the Polish names play with it.

## Smart features are sly, not intelligent

FontLab uses *smart* for a family of features: Smart Corner, Smart Filter, Smart Pencil, smart fill. The rule, from issue 133 and now in the localization principles, is to translate *smart* with a native, simple word for clever or sly, and never with *intelligent*; the German guide adds the hint of peasant cunning (*Bauernschläue*):

| Language | Word | Examples |
|---|---|---|
| German | *schlau* | *Schlaue Ecke*, *Schlauer Filter* |
| Spanish | *astuto/a* | *esquina astuta*, *filtro astuto* |
| French | *futé/e* | *coin futé*, *filtre futé* |
| Polish | *sprytny* | *sprytny narożnik*, *sprytny filtr* |

The founder gave two reasons. *Intelligent* now reads as a claim about artificial intelligence, and people avoid it. And *schlau* is "a bit wannabe smart, which is OK, because it's just software". The German guide adds the word *Bauernschläue*, the shrewdness of a farmer at the market. The rule holds whatever runs inside the feature: a Smart Filter is *Schlauer Filter*, not *intelligenter Filter*, because the word describes how the feature behaves toward the user, not its implementation.

The word inflects normally. A Smart Corner is feminine in German (*schlaue Ecke*) and masculine in Polish (*sprytny narożnik*), and the adjective agrees.

## Terms stay down to earth

The broadest rule is the plainest: prefer simple, ordinary words over sophisticated or technical ones. The Polish list of issue 146 applies it to every name that allowed it:

- **Nudge** is *holowanie*, towing, replacing the earlier *pchnięcie*, a push.
- **Sketchboard** is *szkicownik*, a sketchbook.
- **Skin** is *skórka*, the word for a peel or a rind and for an application skin.
- **Cousins** is *kuzynostwo*, "the cousinhood", a collective noun that also solves a grammar problem ([chapter 408](408-word-formation-and-derivation.md)).
- **Servant node** is *węzeł usłużny*, an obliging node, not a *Servant* in English.

German took the same line where it could: *Skizzenbrett* for Sketchboard, *Schub* for Nudge. The rule meets a limit in [chapter 409](409-do-not-translate-with-restraint.md): a name that denotes one specific operation, such as FontLab's *Oblique* with its built-in optical corrections, can keep its English name because a plain translation would suggest any slant.

Esselink (2000) makes a related point about audience: for novice users a translator may render basic terms that a reference guide for administrators would leave in English. A font editor's audience is expert, but the down-to-earth rule is not about expertise. It is about tone. An expert still prefers *szkicownik* to *Sketchboard* in a Polish sentence.

## Handyman verbs for borrowed tools

Many digital tools borrow their names from physical ones: knife, scissors, pencil, brush, eraser. The founder's rule in issue 147 is that when a real craft has verbs for using the real tool, the translation should adopt them. A knife cuts, scissors snip, an eraser rubs out, a brush paints. The name of the tool sets up an expectation, and the verb should meet it.

The FontLab catalogs of 2026 mostly use neutral software verbs in the tool tips. The table shows the English, what German and Polish currently say, and the craft verb a reviewer might consider. The last column is a set of candidates for review, not shipped decisions.

| Tool tip | German now | Polish now | Craft verb to consider |
|---|---|---|---|
| Knife (J): Add nodes, slice / break contours | *Konturen schneiden / aufbrechen* | *tnij / przerywaj kontury* | already a cutting verb in both |
| Eraser (2): Remove points, simplify paths | *Punkte entfernen* | *Usuwaj punkty* | German *wegradieren*, Polish *wymazuj* |
| Brush (B): Freely draw calligraphic strokes | *frei zeichnen* | *Swobodnie rysuj* | the verb for painting with a brush, where the stroke is painted rather than drawn |
| Scissors (Q): Make overlaps, unlink / loop corners | *erzeugen*, *lösen* | *Twórz*, *rozłączaj* | a snipping verb where the action is a cut |

The rule does not override meaning. The Eraser tool in FontLab removes points and simplifies paths; a craft verb fits because rubbing out is what an eraser does. The Scissors tool makes overlaps and loops corners, which no pair of scissors does, so a snipping verb fits only the cutting part. As always, check the behavior in the running application before adopting a verb.

## Keeping the voice safe

Voice is a reason to choose a word, never a reason to change a meaning. Four checks keep the rules above from going wrong:

1. **The concept first.** Read the definition and the fallback original term ([chapter 404](404-the-fallback-original-term.md)) before looking for a playful word. *Matchmaker* has the fallback *master matcher*; *swat* works because it keeps that meaning.
2. **Survives a missed joke.** The label must be understandable to someone who does not get the reference.
3. **One name everywhere.** A playful name is still a term. *Pędzel mocy* is the same in the toolbar, the menu, the preferences, the help and the marketing page.
4. **Register by surface.** Names can be playful. Error messages, license terms and destructive confirmations stay literal.

## A label can demonstrate its meaning

German **Leer zeichen getrennt** and **Komma,getrennt** are the reviewed
copy-text labels for space-separated and comma-separated output. The spelling
illustrates the separator. Preserve the joke in those controls, while keeping
ordinary *Leerzeichen* elsewhere. A local device is not a new spelling rule,
and a misspelling such as *under* for *unter* is not the same kind of evidence.

## Sources

- Bert Esselink, *A Practical Guide to Localization*, 2000 (chapter 12: terminology setup and target audience)
- `issues/133.md`, `issues/146.md` and `issues/147.md` in the fl10n repository
- `data-fontlab-cpp/i18n/fontlab_de.ts`, `fontlab_es.ts`, `fontlab_fr.ts` and `fontlab_pl.ts` in the fl10n repository
- [localization/principles](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/principles/), [localization/de](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/de/), [localization/es](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/es/) and [localization/fr](https://fontlab.dev/vexy-fontlab-writing-styleguide/fl1992mk/localization/fr/) in the vexy-fontlab-writing-styleguide repository
- `localization/tm/de-core.tmx`, `es-core.tmx`, `fr-core.tmx` and `pl-core.tmx` in the vexy-fontlab-writing-styleguide repository
- `tools/house-rules.md` in the vexy-fontlab-writing-skills repository (rule H14)
