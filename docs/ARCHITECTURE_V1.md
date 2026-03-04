# Discourse Intelligence Engine v1

## Core Word-Based Discourse Analyzer

### Overview

v1 is the **foundational, purely word-based engine**. It focuses on:

- **Basic text statistics** — word and sentence counts.
- **Trigger word profiling** — how much **fear**, **authority**, and **identity** framing is present.
- **Tone detection** — urgent/defensive/fear-oriented labels from surface keywords.
- **Modal & pronoun framing** — obligation language and in‑group vs out‑group structure.
- **Logical fallacy flags** — a few high‑precision, pattern-based fallacies.

Everything in v1 is:

- **Rule-based and deterministic** (no ML, no external APIs).
- **Lexicon and pattern driven** — “word-based, not intelligent” in the sense that it does not try to infer deep meaning, only surface structure.

---

## Module Architecture

```text
src/discourse_engine/
├── main.py           # Pipeline entry point and report formatting (v1/v2 baseline)
├── models/
│   └── report.py     # Report, TriggerProfile, FallacyFlag, AgendaFlag, AssumptionFlag
└── analyzers/
    ├── statistics.py       # Layer 1 – basic counts
    ├── trigger_profile.py  # Layer 2 – fear/authority/identity levels
    ├── tone.py             # Layer 3 – tone labels from keywords
    ├── modal_pronoun.py    # Layer 4 – modal verbs & pronoun framing
    └── logical_fallacy.py  # Layer 5 – core fallacy patterns
```

The same `run_pipeline` function used in later versions still runs this core stack; v1 is best thought of as the **subset of outputs** coming from these analyzers.

---

## 1. Pipeline (v1 View)

Conceptually, the v1 pipeline is:

```text
Input Text
    │
    ├──► StatisticsAnalyzer          → word_count, sentence_count
    ├──► TriggerProfileAnalyzer      → fear/authority/identity levels
    ├──► ToneAnalyzer                → tone labels
    ├──► ModalPronounAnalyzer        → modal verbs, pronoun framing
    └──► LogicalFallacyAnalyzer      → fallacy flags
    │
    ▼
Report (structured output – v1 subset)
```

Later versions add more layers on top (hidden assumptions, hidden agenda, satire/content‑type, narrative/scene/graph models) but **do not change** how these v1 analyzers work.

---

## 2. Statistics Layer

- **Module:** `analyzers/statistics.py`
- **Purpose:** Compute basic text metrics used by other layers and for quick sanity checks.
- **Logic (purely string-based):**
  - Word count = whitespace-split token count.
  - Sentence count = split on `.`, `!`, `?` followed by whitespace.

This gives a cheap notion of document length and density, and provides denominators for later ratios.

---

## 3. Trigger Profile (Fear / Authority / Identity)

- **Module:** `analyzers/trigger_profile.py`
- **Purpose:** Measure how much **fear**, **authority**, and **identity** framing appears, using plain keyword lists.
- **Inputs:** Raw text, optional `lexicon_dir` from `Config`.
- **Logic:**
  - Load term lists from JSON lexicons:
    - `lexicons/fear_terms.json`
    - `lexicons/authority_terms.json`
    - `lexicons/identity_terms.json`
  - Count case‑insensitive matches in the text.
  - Map raw counts to coarse levels:
    - `0` → `Low`
    - `1–2` → `Moderate`
    - `3+` → `High`

Output is a `TriggerProfile` dataclass on the report:

- `fear_level: Low | Moderate | High`
- `authority_level: Low | Moderate | High`
- `identity_level: Low | Moderate | High`

---

## 4. Tone Detection

- **Module:** `analyzers/tone.py`
- **Purpose:** Tag overall rhetorical **tone** from simple keyword sets, without semantic parsing.
- **Logic:**
  - Maintain keyword sets for tones like:
    - **Urgent:** must, need, now, urgent, immediately, crisis, critical.
    - **Defensive:** protect, defend, against, threat, attack.
    - **Fear‑oriented:** fear, afraid, danger, collapse, destroy, threat, catastrophe.
  - If any keyword in a tone set appears in the text, add that tone label.
  - Multiple tones can be active simultaneously.

This layer is deliberately coarse: it answers “does this *sound* urgent/defensive/fearful?” using only surface words.

---

## 5. Modal & Pronoun Framing

- **Module:** `analyzers/modal_pronoun.py`
- **Purpose:** Surface:
  - **Authority / obligation language** (modal verbs).
  - **In‑group vs out‑group structure** via pronouns.

**Modal verbs**

- Extracts modal verbs such as: `must`, `should`, `could`, `would`, `might`, `can`, `will`, `shall`.
- Output: a deduplicated list `modal_verbs_detected` stored on the report.

**Pronoun framing**

- Counts key pronouns: `we`, `they`, `us`, `them`, `I`, `you`, etc.
- Stores counts in `pronoun_framing` (e.g. `{"we": 3, "they": 2}`).
- When both in‑group pronouns (`we`, `us`) and out‑group pronouns (`they`, `them`) are present, emits a simple insight string such as:
  - `"Possible in-group / out-group framing."`

All of this is strictly token-based; no coreference or entity resolution is attempted in v1.

---

## 6. Logical Fallacy Flags (Core Set)

- **Module:** `analyzers/logical_fallacy.py`
- **Purpose:** Flag a **small, conservative set** of recognizable fallacies using regex/pattern matching.

The emphasis in v1 is **precision over coverage**: only patterns that can be identified reliably with surface forms are included, such as:

- **False Dilemma**
  - Pattern: `\beither\b ... \bor\b ...`
  - Guard rails to avoid genuine dichotomies (e.g. “either it exists or it doesn't”).
- **Appeal to Fear**
  - Uses threat‑related terms (collapse, destroy, threat, danger, catastrophe, crisis).
- **Ad Hominem / Attack**
  - Patterns like “they want to [verb]”, framing a group as malicious.

Each detection becomes a `FallacyFlag`:

- `name` — human‑readable label (“False Dilemma”).
- `pattern_hint` — short hint of which rule fired.
- `sentence` — the source sentence.
- `confidence` — a 0–1 heuristic score (defaults can be 0.0 in simple cases).

---

## 7. Report (v1 Subset)

The full `Report` dataclass (used by later versions) contains more fields, but the **v1 view** is the subset directly produced by the analyzers above:

- `word_count`, `sentence_count`
- `trigger_profile` (fear/authority/identity levels)
- `tone` (list of tone labels)
- `modal_verbs_detected`
- `pronoun_framing`, `pronoun_insight`
- `logical_fallacy_flags`

Higher versions (v2–v5) extend this with hidden assumptions, hidden agenda flags, satire/content‑type hints, narrative features, dialogue metrics, and discourse graphs.

---

## 8. Usage (CLI & Python)

Even though the implementation has grown beyond v1, the same interfaces expose the v1‑style analysis:

### CLI

```bash
python -m discourse_engine "Either we pass this law, or our nation will collapse."
```

### Python API

```python
from discourse_engine import run_pipeline, format_report

report = run_pipeline("Either we pass this law, or our nation will collapse.")
print(report.word_count, report.trigger_profile, report.tone)
print(format_report(report))
```

If you only care about the **v1 layer**, you can ignore hidden‑assumption / hidden‑agenda fields in the report and treat it as a strictly word‑based analyzer.

