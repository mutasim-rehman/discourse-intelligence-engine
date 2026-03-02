# Future Work

Features not yet implemented and planned enhancements for the Discourse Intelligence Engine.

---

## 1. LLM-Based Hidden Assumption Extraction

**Status:** Stub present; API integration not implemented

**Current:** Rule-based patterns only (presuppositions, enthymemes, epistemic shortcuts).

**Planned:** Optional LLM call (OpenAI/Anthropic) for deeper inference:

- Detect assumptions that rules miss (e.g., complex causal leaps, implicit values)
- Extract explicit assumption text rather than just pattern labels
- Prompt template: "Extract hidden assumptions in the following text. List each as a short phrase."

**Requirements:** `openai>=1.0` (optional dependency); API key via `Config.llm_api_key`

**Design:** `HiddenAssumptionExtractor` already accepts `api_key` and `model`. Add fallback: if `api_key` is None, use rule-based only; otherwise call LLM and merge or replace results.

---

## 2. Additional Logical Fallacies

**Status:** Partially implemented (3 types)

**Not yet implemented:**

- **Straw man** — Misrepresenting opponent's position
- **Red herring** — Irrelevant diversion
- **Slippery slope** — Unwarranted chain of consequences
- **Appeal to authority** — Citing authority without relevance
- **Bandwagon** — "Everyone believes X"
- **Hasty generalization** — Sample-to-population leap
- **Circular reasoning** — Conclusion as premise

**Challenges:** Many require semantic understanding. Rule-based patterns exist for some (e.g., "if X then Y then Z" for slippery slope) but produce false positives.

---

## 3. Additional Hidden Agenda Techniques

**Status:** 5 families, ~10 techniques implemented

**From Media Bias Elements taxonomy (38 types), not yet implemented:**

- **Confirming:** Cherry-picking, Anecdotal evidence, Social compliance, Source selection
- **Dividing:** Discriminatory bias (stereotype patterns)
- **Misreasoning:** Causal misunderstanding, Circular reasoning, Burden of proof, Generalization
- **Personalizing:** Association bias, Horse race bias
- **Preferring:** Conflict of interest (requires external knowledge)
- **Framing:** Word choice (connotative), Name-calling, Labeling, Metaphor, Scope framing

**Priority:** Cherry-picking (sentence-level indicators like "only half" without context), Causal misunderstanding ("X caused Y" without evidence), Association bias ("linked to", "associated with" negatively).

---

## 4. Sentence-Level Span Annotation

**Status:** Not implemented

**Current:** Flags apply to whole text. No character offsets or sentence-level attribution.

**Planned:**

- Return `(start, end, flag)` or `(sentence_index, flag)` for each detection
- Enable highlighting in UI or inline annotation
- Useful for tools like BiasScanner-style browser add-ons

---

## 5. Multi-Language Support

**Status:** English-only

**Planned:**

- Lexicons and patterns for German, Spanish, etc.
- Language detection or explicit `lang` parameter
- Locale-specific presupposition triggers and agenda patterns

---

## 6. NLTK / Enhanced Tokenization

**Status:** Optional in `requirements.txt`; not used

**Planned:**

- Use NLTK for sentence segmentation (handles abbreviations, etc.)
- Use NLTK for word tokenization (better than whitespace split)
- Part-of-speech tagging for more accurate modal/pronoun detection

---

## 7. Confidence Scores

**Status:** Not implemented

**Current:** Binary detection (present/absent).

**Planned:**

- Confidence or strength score per flag (e.g., 0–1)
- Based on pattern match strength, multiple indicators, or lexicon hit count
- Allow filtering by threshold in report or API

---

## 8. Output Formats

**Status:** Human-readable text and Python `Report` object only

**Planned:**

- **JSON** — Structured export for integration
- **Markdown** — For documentation and sharing
- **HTML** — For web display with highlighted spans

---

## 9. Streaming / Chunked Analysis

**Status:** Full-text analysis only

**Planned:**

- Process long documents in chunks (e.g., by paragraph)
- Aggregate or merge results across chunks
- Useful for articles, transcripts, scripts

---

## 10. Explainability Module

**Status:** Pattern hints only

**Planned:**

- Per-flag explanation: what was matched, why it matters
- Short educational blurbs (e.g., "False dilemma: presents two options as the only ones when more exist")
- Link to media literacy resources

---

## 11. Configuration for Sensitivity

**Status:** Fixed thresholds (e.g., fear count → Low/Moderate/High)

**Planned:**

- Configurable sensitivity (strict / balanced / lenient)
- Per-analyzer enable/disable
- Custom pattern or lexicon injection via config

---

## 12. Benchmark and Evaluation

**Status:** No automated evaluation

**Planned:**

- Gold-standard dataset with human annotations
- Precision, recall, F1 per analyzer
- Regression tests on curated examples

---

## 13. API / Web Service

**Status:** CLI and Python API only

**Planned:**

- REST or FastAPI endpoint
- Rate limiting, authentication
- Async processing for long texts

---

## 14. Browser Extension / Web Demo

**Status:** Not implemented

**Planned:**

- Highlight bias/fallacy/assumption spans on news articles
- Popover explanations on hover
- Similar to BiasScanner (biasscanner.org)

---

## Accuracy Improvements Requiring New Dependencies

The following accuracy improvements were identified but require new dependencies or infrastructure:

### Step 1 — Dependency Parsing & Clause Detection

**Status:** Not implemented (requires spaCy or Stanza)

**Planned:** Use dependency parsing and semantic role labeling to:

- Identify main vs. subordinate clauses for more precise presupposition attribution
- Improve causal extraction ("X causes Y") by parsing argument structure
- Reduce false positives in structural patterns via syntactic validation

**Requirements:** `spacy` or `stanza` with English models

---

### Step 2 — Gold Standard Dataset

**Status:** Not implemented

**Planned:** Create a curated dataset of 50–100 annotated paragraphs to:

- Benchmark precision, recall, and F1 per analyzer
- Tune confidence thresholds and scoring weights
- Enable regression testing on representative examples

**Requirements:** Manual annotation effort; optional storage format (JSON/JSONL)

---

### Step 6 — NLI for Entailment/Contradiction Checks

**Status:** Not implemented (requires NLI model)

**Planned:** Use Natural Language Inference (e.g. RoBERTa-MNLI, DeBERTa) to:

- Validate whether stated premises entail the conclusion (enthymeme detection)
- Flag contradictions between sentences
- Reduce false positives when inference is explicitly supported

**Requirements:** `transformers`, `torch` (or similar); GPU optional for speed

---

## Summary Table


| Feature                 | Effort | Impact | Priority |
| ----------------------- | ------ | ------ | -------- |
| LLM hidden assumptions  | Medium | High   | High     |
| Sentence-level spans    | Medium | High   | High     |
| JSON/HTML output        | Low    | Medium | Medium   |
| Additional fallacies    | Medium | Medium | Medium   |
| Additional agenda types | Medium | Medium | Medium   |
| Multi-language          | High   | High   | Medium   |
| Confidence scores       | Medium | Medium | Low      |
| Config sensitivity      | Low    | Low    | Low      |


