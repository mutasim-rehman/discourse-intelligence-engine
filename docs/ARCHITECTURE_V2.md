# Discourse Intelligence Engine v2

## Structured Assumptions & Hidden Agenda Layer

### Overview

v2 builds on the **word-based v1 core** by adding:

- **Hidden assumption extraction** — presuppositions, epistemic shortcuts, universal claims, enthymemes, loaded questions, vague authority.
- **Hidden agenda detection** — deflecting, dividing, asserting, personalizing, and framing techniques inspired by the Media Bias Elements taxonomy.
- A richer **structured report model** (`AssumptionFlag`, `AgendaFlag`) for downstream tools.

It is still:

- **Rule‑based and offline** — no external APIs required.
- **Surface‑driven but more “intelligent”** — uses linguistic triggers and discourse patterns to infer *unstated premises* and *strategic moves*, not just counts.

---

## Module Architecture

```text
src/discourse_engine/
├── main.py                 # Pipeline entry + v2 orchestration
├── models/
│   └── report.py           # Report, TriggerProfile, FallacyFlag, AgendaFlag, AssumptionFlag
└── analyzers/
    ├── statistics.py
    ├── trigger_profile.py
    ├── tone.py
    ├── modal_pronoun.py
    ├── logical_fallacy.py
    ├── hidden_assumptions.py   # NEW in v2
    └── hidden_agenda.py        # NEW in v2
```

`run_pipeline` in `main.py` now orchestrates both the **v1 analyzers** and these new v2 layers, returning a single enriched `Report`.

---

## 1. Pipeline (v2 View)

At v2, the conceptual pipeline is:

```text
Input Text
    │
    ├──► StatisticsAnalyzer          → word_count, sentence_count
    ├──► TriggerProfileAnalyzer      → fear/authority/identity levels
    ├──► ModalPronounAnalyzer        → modal verbs, pronoun framing
    ├──► LogicalFallacyAnalyzer      → fallacy flags
    ├──► HiddenAssumptionExtractor   → assumption flags (new)
    ├──► HiddenAgendaAnalyzer        → agenda flags (new)
    └──► ToneAnalyzer                → tone from keywords + pragmatic signals
    │
    ▼
Report (enriched v2 output)
```

Two key changes relative to v1:

- New analyzers **infer implicit content** (assumptions, agendas).
- The **tone layer** can incorporate signals from fallacies and agenda flags (pragmatic bridge rules in `main.py`).

---

## 2. Hidden Assumption Extraction

- **Module:** `analyzers/hidden_assumptions.py`
- **Purpose:** Detect **unstated premises and beliefs** implied by the wording, drawing on presupposition theory and argumentation heuristics.

### 2.1 Presupposition Triggers

Looks for words that *presuppose* something is already true, such as:

- **Factive verbs:** know, realize, discover, regret → assume the complement is true.
- **Implicative verbs:** manage, fail, avoid, forget → imply prior attempts or outcomes.
- **Change‑of‑state verbs:** begin, stop, continue, resume → assume a previous state.
- **Repetition markers:** again, still, return → assume prior occurrence.

Example:

- “He realized the policy had failed.”
  - Implied assumption: *“The policy had failed” is taken as given.*

### 2.2 Epistemic Shortcuts

Flags phrases that present a claim as **obvious or settled** without argument, e.g.:

- obviously, clearly, of course, needless to say, as we all know.

These are turned into assumption descriptions like *“Presents claim as obvious without justification (epistemic shortcut).”*

### 2.3 Universal Quantifiers

Detects blanket generalizations using:

- everyone, nobody, always, never, all, none, etc.

Example:

- “Everyone knows this is wrong.”
  - Implied assumption: *“This is universally accepted as wrong.”*

### 2.4 Enthymeme / Conclusion Markers

Looks for conclusion markers:

- therefore, thus, hence, consequently, so.

These often signal **missing premises** (enthymemes):

- “The evidence is in. Therefore we must act.”
  - Assumption: *“The evidence is sufficient / conclusive.”*

### 2.5 Loaded Questions & Vague Authority

- **Loaded questions:** “Why do you still X?”, “When did you stop X?” → presuppose guilt or prior behavior.
- **Vague authority:** experts, studies show, many believe, widely known → invoke unspecified backing.

### 2.6 Data Model

Each detection becomes an `AssumptionFlag`:

- `description` — human‑readable explanation of the assumption.
- `sentence` — the source sentence.
- `confidence` — optional 0–1 score (future‑proofed for ML/LLM enhancement).

These populate `report.hidden_assumptions`.

---

## 3. Hidden Agenda Detection

- **Module:** `analyzers/hidden_agenda.py`
- **Purpose:** Detect **strategic discourse moves** that signal bias or manipulation, inspired by the Media Bias Elements taxonomy.

It groups techniques into several families; key ones include:

### 3.1 Deflecting

- **Whataboutism:** “what about”, “how about when …”
- **Shifting goalpost:** “this is not X, it’s Y”
- **Side note / diversion:** “Meanwhile…”, “In other news…”

These suggest **topic diversion** or changing the evaluation frame.

### 3.2 Dividing

- **Us vs Them:** `they want/are/will` + hostile verbs/terms.
- **Gatekeeping:** “only real”, “true patriots”, “genuine supporters”.

These highlight language that sharpens **in‑group vs out‑group** divides.

### 3.3 Asserting

- **Speculation:** rumors, allegedly, reportedly.
- **Vagueness:** experts say, studies show, many people think…

Patterns where **uncertain or unnamed sources** are used to present claims as solid.

### 3.4 Personalizing

- **Mud & Honey:** hypocrite, liar, fraud, etc., focusing on character rather than argument.

### 3.5 Framing / Emotional Sensationalism

- **Emotional sensationalism:** over‑reliance on fear lexicon (collapse, threat, danger, crisis…).

### 3.6 Data Model

Each match yields an `AgendaFlag`:

- `family` — e.g. `Dividing`, `Deflecting`, `Framing`.
- `technique` — specific technique (`Us vs Them`, `Whataboutism`, etc.).
- `pattern_hint` — which rule fired.
- `sentence` — source sentence.
- `confidence` — optional 0–1 strength score.

These populate `report.hidden_agenda_flags`.

---

## 4. Pragmatic Tone Bridge (v2 Integration)

In `main.py`, after running all analyzers, v2 **lets pragmatic signals shape the final tone labels**:

- If any agenda flag has family `Face-threatening act` → inject a **“Coercive/Passive‑Aggressive”** tone.
- If any agenda flag has family `Obscuration` → inject **“Clinical/Evasive”** tone.
- If fallacies include **Appeal to Fear** → inject **“Alarmist”** tone.

This keeps tone **lexical at the core** but allows hidden‑agenda and fallacy signals to refine how the system characterizes the discourse.

---

## 5. Report (v2 View)

The v2 report extends the v1 subset:

- **Baseline (from v1):**
  - `word_count`, `sentence_count`
  - `trigger_profile` (fear/authority/identity)
  - `tone`
  - `modal_verbs_detected`
  - `pronoun_framing`, `pronoun_insight`
  - `logical_fallacy_flags`

- **New in v2:**
  - `hidden_assumptions: list[AssumptionFlag]`
  - `hidden_agenda_flags: list[AgendaFlag]`
  - (Plus satire/content‑type fields, which are further expanded in later versions.)

Downstream tools can choose to:

- Show a **“v1 view”** (core lexical + fallacies only), or
- Use the **full v2 report** with assumptions and agenda techniques.

---

## 6. Usage

The same CLI and Python API used in v1 now expose v2 information:

```python
from discourse_engine import run_pipeline

report = run_pipeline("Obviously, we need to act now. Experts agree this is the only option.")

for a in report.hidden_assumptions:
    print(a.description, "→", a.sentence)

for f in report.hidden_agenda_flags:
    print(f.family, "/", f.technique, "→", f.sentence)
```

This is the “some intelligent one” layer: still deterministic and lexicon‑driven, but designed to surface **what is being taken for granted** and **how the conversation is being steered**, not just which words appear.

