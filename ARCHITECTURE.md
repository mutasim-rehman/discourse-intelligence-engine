# Architecture

This document describes each layer of the Discourse Intelligence Engine, the underlying logic, and illustrative examples.

---

## Pipeline Overview

```
Input Text
    │
    ├──► StatisticsAnalyzer          → word_count, sentence_count
    ├──► TriggerProfileAnalyzer      → fear/authority/identity levels
    ├──► ToneAnalyzer                → tone labels
    ├──► ModalPronounAnalyzer        → modal verbs, pronoun framing
    ├──► LogicalFallacyAnalyzer      → fallacy flags
    ├──► HiddenAssumptionExtractor   → assumption descriptions
    └──► HiddenAgendaAnalyzer        → agenda technique flags
    │
    ▼
Report (structured output)
```

All analyzers are stateless and rule-based. No external APIs are used.

---

## Layer 1: Statistics

**Module:** `analyzers/statistics.py`

**Purpose:** Compute basic text metrics.

**Logic:**
- **Word count:** Whitespace-split token count
- **Sentence count:** Split on `.!?` followed by whitespace

**Example:**
```
Input:  "Either we pass this law, or our nation will collapse."
Output: word_count=9, sentence_count=1
```

---

## Layer 2: Trigger Profile

**Module:** `analyzers/trigger_profile.py`

**Purpose:** Measure the intensity of fear, authority, and identity framing using lexicons.

**Logic:**
- Load terms from `lexicons/fear_terms.json`, `authority_terms.json`, `identity_terms.json`
- Count matches (case-insensitive) in the text
- Map counts to levels:
  - 0 → Low
  - 1–2 → Moderate
  - 3+ → High

**Why it matters:** These dimensions correlate with persuasive and polarizing discourse. High fear/authority/identity often indicates emotionally charged or agenda-driven text.

**Example:**
```
Input:  "We must protect our people from this growing threat. They want to destroy everything."
        (fear: threat, destroy; authority: must; identity: we, our, they)
Output: fear_level=Moderate, authority_level=Moderate, identity_level=Moderate
```

---

## Layer 3: Tone

**Module:** `analyzers/tone.py`

**Purpose:** Detect dominant rhetorical tone via keyword sets.

**Logic:**
- **Urgent:** must, need, now, urgent, immediately, critical, crisis
- **Defensive:** protect, defend, against, threat, attack, stand for
- **Fear-oriented:** fear, afraid, danger, collapse, destroy, threat, crisis

Multiple tones can be present. Labels are appended if any keyword in the set appears.

**Example:**
```
Input:  "We must protect our people from this threat."
Output: ["Urgent", "Defensive", "Fear-oriented"]
```

---

## Layer 4: Modal & Pronoun Analysis

**Module:** `analyzers/modal_pronoun.py`

**Purpose:** Surface authority framing and in-group/out-group structure.

**Logic:**
- **Modal verbs:** Extract must, should, could, would, might, can, will, shall (deduplicated)
- **Pronouns:** Count we, they, us, them, I, you
- **Insight:** If both we/us and they/them appear, flag "Possible in-group / out-group framing"

**Why it matters:** Pronoun asymmetry (we vs they) is a hallmark of polarizing rhetoric. Modal verbs (must, should) convey obligation and authority.

**Example:**
```
Input:  "We must protect our people. They want to destroy."
Output: modal_verbs=["must"], pronoun_framing={"we":1, "they":1},
        pronoun_insight="Possible in-group / out-group framing"
```

---

## Layer 5: Logical Fallacy Detection

**Module:** `analyzers/logical_fallacy.py`

**Purpose:** Flag common argumentative errors via pattern matching.

### 5.1 False Dilemma

**Logic:** Detect "either X or Y" but exclude genuine dichotomies (X vs not-X).

- Match: `\beither\b.*\bor\b`
- Exclude if second option negates the first (doesn't, isn't, not, never) or is a complementary pair (true/false, yes/no)

**Example (flagged):**
```
"Either you support this bill or you hate this country."
→ False Dilemma (pattern: either X or Y)
```

**Example (not flagged):**
```
"Either the file exists or it doesn't."
→ Genuine dichotomy, no flag
```

### 5.2 Appeal to Fear

**Logic:** Presence of threat-related terms: collapse, destroy, threat, danger, catastrophe, crisis.

**Example:**
```
"Our nation will collapse."
→ Appeal to Fear (threat language)
```

### 5.3 Ad Hominem / Attack

**Logic:** Pattern "they want to [verb]" — attributes hostile intent to out-group.

**Example:**
```
"They want to destroy everything we stand for."
→ Ad Hominem / Attack (they want to [verb] pattern)
```

---

## Layer 6: Hidden Assumptions

**Module:** `analyzers/hidden_assumptions.py`

**Purpose:** Detect unstated premises and implicit beliefs using linguistic triggers from argumentation theory and pragmatics.

### 6.1 Presupposition Triggers

| Type | Examples | Implication |
|------|----------|-------------|
| Factive verbs | know, realize, discover, regret | Assumes complement is true |
| Implicative verbs | manage, avoid, forget | Implies prior attempt/action |
| Change-of-state | begin, stop, continue, resume | Assumes prior state |
| Repetition | again, still, return | Assumes prior occurrence |

**Example:**
```
"He realized the policy had failed."
→ Presupposition (factive verb: 'realized') — treats "policy had failed" as given
```

### 6.2 Epistemic Shortcuts

**Logic:** Phrases that present claims as obvious without justification: obviously, clearly, of course, needless to say, as we all know.

**Example:**
```
"Obviously, we need to act now."
→ Presents claim as obvious without justification (epistemic shortcut)
```

### 6.3 Universal Quantifiers

**Logic:** everyone, nobody, always, never, all — imply shared belief or blanket generalization.

**Example:**
```
"Everyone knows this is wrong."
→ Unstated universal claim: implies shared belief or blanket generalization
```

### 6.4 Conclusion Markers (Enthymeme)

**Logic:** therefore, thus, hence, so, consequently — suggest inference without full stated premises.

**Example:**
```
"The evidence is in. Therefore we must act."
→ Conclusion marker suggests inference without full stated premises (enthymeme)
```

### 6.5 Loaded Questions

**Logic:** "Why do you still X?", "When did you stop X?" — imply guilt/support in the question.

**Example:**
```
"Why do you still support that policy?"
→ Loaded question: implies an assumption in the question itself
```

### 6.6 Vague Authority

**Logic:** experts, studies show, many believe, widely known — invoke unspecified support.

**Example:**
```
"Experts agree that this is the best approach."
→ Vague authority invoked without specification
```

---

## Layer 7: Hidden Agenda Detection

**Module:** `analyzers/hidden_agenda.py`

**Purpose:** Identify strategic discourse patterns that suggest deflection, division, assertion without evidence, personalization, or framing.

Based on the Media Bias Elements taxonomy (38 bias types in 8 families). This layer implements the rule-detectable subset.

### 7.1 Deflecting

| Technique | Patterns | Example |
|-----------|----------|---------|
| Whataboutism | "what about", "how about when" | "But what about when they did the same?" |
| Shifting Goalpost | "this is not X, it's Y" | "This is not a bailout, it's support." |
| Side Note | "Meanwhile", "In other news" | "Meanwhile, another scandal broke." |

### 7.2 Dividing

| Technique | Patterns | Example |
|-----------|----------|---------|
| Us vs Them | "they want/are/will", hostile terms | "They want to destroy." / "poisoning" |
| Gatekeeping | "only real", "true patriots", "genuine" | "The only real union is the CWA." |

### 7.3 Asserting

| Technique | Patterns | Example |
|-----------|----------|---------|
| Speculation | rumors, allegedly, reportedly | "Rumors suggest he will resign." |
| Vagueness | experts say, studies show, many people | "Many critics say the plan will fail." |

### 7.4 Personalizing

| Technique | Patterns | Example |
|-----------|----------|---------|
| Mud & Honey | hypocrite, liar, fraud, derogatory framing | "He's a hypocrite." |

### 7.5 Framing

| Technique | Logic | Example |
|-----------|-------|---------|
| Emotional Sensationalism | Fear lexicon (collapse, threat, danger) | Any text with fear terms |

**Example (combined):**
```
"They want to destroy everything. But what about their record? This is not a bailout."
→ Us vs Them, Whataboutism, Shifting Goalpost
```

---

## Report Structure

```python
@dataclass
class Report:
    word_count: int
    sentence_count: int
    trigger_profile: TriggerProfile
    tone: list[str]
    modal_verbs_detected: list[str]
    pronoun_framing: dict[str, int]
    pronoun_insight: str | None
    logical_fallacy_flags: list[FallacyFlag]
    hidden_assumptions: list[str]
    hidden_agenda_flags: list[AgendaFlag]
```

---

## Lexicons

Stored as JSON arrays in `lexicons/`:

- **fear_terms.json** — collapse, destroy, threat, danger, fear, terror, crisis, catastrophe, disaster, etc.
- **authority_terms.json** — terms invoking authority or expertise
- **identity_terms.json** — terms related to group identity

Lexicons are loaded at analyzer init. Custom `lexicon_dir` can be passed via `Config`.

---

## Design Principles

1. **Rule-based first** — No external APIs; all detection is deterministic and offline.
2. **Modular analyzers** — Each layer is independent; easy to add or remove.
3. **Pattern transparency** — Each flag includes a `pattern_hint` for interpretability.
4. **Lexicon extensibility** — Swap JSON files for domain adaptation.
