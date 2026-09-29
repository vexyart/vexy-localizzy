---
this_file: src_docs/md/6-machine-translation/index.md
---

# Part 6. Machine translation and AI

A language model can draft ten thousand interface strings overnight, and every one of them will read well. This part is about making that draft trustworthy. It traces machine translation from rule-based systems to large language models, then follows a string through a working pipeline: the context a model needs to translate a label correctly, the memories that should answer before any model is asked, the glossary terms sent with each batch and checked afterwards in every inflected form, the placeholder protocol that keeps a translation from breaking the application, and the choices of model, batch size and cache that decide what a run costs. It then weighs automatic quality scores and language-model judges against human review, describes what a post-editor does with a draft and how recurring edits become glossary entries, and ends with provider terms, privacy and the records that make a machine-assisted catalog reproducible. The vexy-localizzy toolkit and the FontLab German, Spanish, French and Polish catalogs supply the worked examples; the reasoning applies to any team that uses a model to translate software.

- [601. What this part knows](601-what-this-part-knows.md)
- [602. From rules to models: statistical, neural and large language model translation](602-from-rules-to-models.md)
- [603. Context engineering: what a model needs to translate a label correctly](603-context-engineering.md)
- [604. Memory-first pipelines: kept, memory, engine, pending](604-memory-first-pipelines.md)
- [605. Glossary enforcement: sending the right terms, checking that they arrived](605-glossary-enforcement.md)
- [606. The placeholder protocol: parse, instruct, validate, repair](606-the-placeholder-protocol.md)
- [607. Routing, batching, caching and cost: which model for which string](607-routing-batching-and-cost.md)
- [608. Quality estimation and judges: QE metrics, LLM-as-judge, MQM scoring and their limits](608-quality-estimation-and-judges.md)
- [609. Post-editing: what a human does with a draft, and how the draft-to-final diff feeds the glossary](609-post-editing.md)
- [610. Data terms, privacy and trust: unreleased strings, provider policies and reproducibility](610-data-terms-and-trust.md)
