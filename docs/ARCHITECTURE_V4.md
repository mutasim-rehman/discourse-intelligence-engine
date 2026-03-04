# Discourse Intelligence Engine v4

## Dialogue-Focused Analysis & Power Dynamics

### Overview

v4 extends the engine from **single‑voice texts** to **multi‑speaker dialogues** (interviews, debates, hearings, podcasts). It models:

- **Turn‑level structure** — who speaks when, with what content.
- **Contradictions between speakers** — using v3 contradiction logic, aggregated per speaker pair.
- **Question dodging / evasion** — how directly answers address preceding questions.
- **Power dynamics** — dominance and authority per speaker based on language and turn patterns.
- **Topic threading / unresolved entities** — which topics/questions remain unanswered.

v4 is still **rule‑based** and offline; it reuses many of the lexical ideas from v1/v2, but at the **dialogue level**.

---

## Module Architecture

```text
src/discourse_engine/
├── v4/
│   ├── __init__.py          # "v4 dialogue-focused analysis modules."
│   ├── models.py            # Dialogue, DialogueTurn, SpeakerProfile, DialogueReport, ...
│   ├── dialogue_pipeline.py # High-level dialogue pipeline + CLI/report helpers
│   ├── contradiction.py     # DialogueContradictionAnalyzer (wraps v3 contradiction)
│   ├── evasion.py           # DialogueEvasionAnalyzer (question dodging)
│   ├── power_dynamics.py    # PowerDynamicsAnalyzer (dominance/authority)
│   ├── topic_tracker.py     # TopicTracker (unresolved entities)
│   └── io.py                # STT/diarization adapter interfaces
└── __main__.py
    ├── --dialogue           # Enable v4 analysis for speaker-tagged transcripts
    └── --dialogue-json      # Export v4 dialogue report as JSON
```

The v4 API is also re‑exported from `src/discourse_engine/__init__.py`:

- `parse_speaker_tagged_text`
- `run_dialogue_analysis`
- `dialogue_report_to_dict`
- `format_dialogue_report`
- `DialogueReport`

---

## 1. Dialogue Data Model

- **Module:** `v4/models.py`

Core classes:

- `SpeakerProfile`
  - `speaker_id` — stable identifier (e.g. `interviewer`, `politician`).
  - `display_name` — human‑readable label.
  - `role` — optional semantic role (e.g. “Journalist”, “CorporateExecutive”).
  - `metadata` — arbitrary extra fields.

- `DialogueTurn`
  - `speaker_id`, `text`, `turn_index`.
  - Optional `display_name`, `role`.
  - Optional `start_time`, `end_time` for audio/video alignment.
  - Optional `acoustic_features` and `metadata`.

- `Dialogue`
  - Container of `turns: list[DialogueTurn]`.
  - `speaker_profiles: dict[str, SpeakerProfile]`.

- `DialogueReport`
  - Top‑level v4 output with:
    - `dialogue`
    - `contradictions: ContradictionMatrix | None`
    - `evasion: EvasionSummary | None`
    - `power_dynamics: PowerDynamicsSummary | None`
    - (plus a dynamically attached `topics: TopicTrackerSummary | None` in the pipeline).

These dataclasses make it easy to plug v4 into other tools and serialize to JSON.

---

## 2. Dialogue Ingestion & Parsing

- **Module:** `v4/dialogue_pipeline.py`

### 2.1 `parse_speaker_tagged_text`

Parses simple **speaker‑tagged transcripts** into a `Dialogue`:

- **Primary path (interview style):**
  - Detects labels such as `Interviewer:` and `Politician:` embedded in the text.
  - Splits with a regex and converts each labelled segment into a `DialogueTurn`.
- **Fallback path:**
  - Treats each line starting with `Speaker:` as `LABEL: text`.
  - Lines without a new label extend the previous speaker’s turn, or create an anonymous `speaker` profile if none exists yet.

Speaker IDs are normalized to lowercase, underscore‑separated identifiers using `_normalize_speaker_id`.

### 2.2 Audio / STT Ingestion

- **Module:** `v4/io.py`

Provides abstract adapters:

- `STTAdapter` — interface for speech‑to‑text backends (Whisper, Google STT, etc.).
- `DiarizationAdapter` — interface for standalone diarization.
- `dialogue_from_stt(adapter, audio_path)` — helper to construct a `Dialogue` from an `STTAdapter` implementation.

This keeps v4 independent of any particular audio provider.

---

## 3. Dialogue Pipeline & Entry Points

- **Module:** `v4/dialogue_pipeline.py`

High‑level functions:

- `dialogue_from_turns(turns)` — builds a `Dialogue` from existing `DialogueTurn` objects.
- `run_dialogue_analysis(turns)` — v4 **entry point**:
  - Wraps turns in a `Dialogue`.
  - Runs:
    - `DialogueContradictionAnalyzer`
    - `DialogueEvasionAnalyzer`
    - `PowerDynamicsAnalyzer`
    - `TopicTracker`
  - Returns a `DialogueReport` with all subreports attached.
- `run_dialogue_from_text(text)` — convenience wrapper:
  - `parse_speaker_tagged_text(text)` → `run_dialogue_analysis(...)`.

Formatting & export:

- `dialogue_report_to_dict(report)` — JSON‑serializable dict (used by `--dialogue-json`).
- `format_dialogue_report(report)` — human‑readable CLI summary (“--- V4 Dialogue Analysis ---”).

---

## 4. Contradiction Matrix (Cross‑Speaker)

- **Module:** `v4/contradiction.py`
- **Purpose:** Build a **speaker‑pair contradiction matrix** from a `Dialogue`.

### 4.1 Core Logic

- Reuses v3’s `ContradictionAnalyzer`:
  - Converts turns to `(speaker_id, text)` pairs.
  - Runs the v3 analyzer with a configurable `min_overlap` threshold.
- Aggregates results per speaker pair into `ContradictionCell` objects:
  - `speaker_a`, `speaker_b`
  - `contradictions` — count of contradiction instances.
  - `strongest_score` — max probability observed.
- Wraps all cells in a `ContradictionMatrix` with a short summary string.

### 4.2 Fallback via Evasion

When no **direct** contradictions are found:

- v4 falls back to **contextual contradictions**:
  - Runs `DialogueEvasionAnalyzer`.
  - If aggregate evasion is high and some answers have both:
    - very low lexical overlap with their questions, and
    - high evasion scores,
  - It synthesizes a symmetric contradiction cell for the two speakers, treating repeated evasive non‑answers as an implicit contradiction.

This way, v4 can still flag tension between speakers even when surface negation is subtle.

---

## 5. Evasion (Question Dodging)

- **Module:** `v4/evasion.py`
- **Purpose:** Score how directly answers address prior questions.

Key pieces:

- `_is_question(text)` — identifies question turns based on:
  - Trailing `?`.
  - Presence of wh‑words (what, when, where, why, how, who, which) or auxiliaries (do, is, can, will, should, have, …).
- For each question turn:
  - Finds the **first subsequent turn** from a different speaker as the primary answer.
  - Computes:
    - **Semantic overlap** between question and answer via shared ≥3‑character words.
    - **Hedging density** — frequency of hedging terms (perhaps, maybe, might, could, allegedly, …).
    - **Content‑word coverage** — overlap of content words (non‑stopwords) between question and answer.
  - Base evasion score:
    - High when overlap is low and hedging is high.
    - Boosted to ≥0.75 when key content words from the question never appear in the answer.
  - If the answer contains a **Red Herring** fallacy (via `LogicalFallacyAnalyzer`), score is forced high (≥0.8).

Low scores (< 0.15) are discarded as non‑evasive.

Outputs:

- `EvasionScore` for each flagged answer:
  - `turn_index`, `question_index`, `score`, `reason`.
- `EvasionSummary`:
  - `scores` list.
  - `aggregate_score`.
  - Human‑readable `summary`.

---

## 6. Power Dynamics

- **Module:** `v4/power_dynamics.py`
- **Purpose:** Infer **who is dominant / authoritative** in the dialogue from lexical and turn patterns.

Per speaker, the analyzer accumulates:

- `total_turns`, `total_tokens`.
- `interruption_count` — short turns that immediately follow a different speaker.
- Average scores from each turn:
  - **Intensity** (fear/urgency lexicon).
  - **Dominance** (strong modal/absolute terms: must, shall, will, cannot, never, always, everyone).
  - **Certainty** (certainty modals subset).

These become `SpeakerPowerMetrics`:

- `dominance_score` — normalized so the most dominant speaker ≈ 1.0.
- `authority_score` — normalized certainty score.

`PowerDynamicsSummary` contains:

- `speakers: list[SpeakerPowerMetrics]`
- `summary` — e.g. “Most dominant speaker: X (dominance=0.95, authority=0.87).”

---

## 7. Topic Threading & Unresolved Entities

- **Module:** `v4/topic_tracker.py`
- **Purpose:** Track **topical entities** in questions that are repeatedly not addressed.

Core idea:

- For each question turn:
  - Find the next answer from a different speaker.
  - Extract **content words** (non‑stopwords) from question and answer.
  - Compute coverage of question entities in the answer.
  - If coverage < 0.2:
    - Treat entities from the question as **further evaded**; increment counters.
  - If coverage is good:
    - Reset counters for the shared entities.

Aggregates into:

- `TopicEntity` (`entity`, `consecutive_evasions`).
- `TopicTrackerSummary`:
  - `entities` list.
  - `summary` like:
    - `"Unresolved entities: 'Zurich' evaded for 3 consecutive turn(s); '$500' evaded for 2 consecutive turn(s)."`

This gives a **threaded view** of what topics are asked about but not answered.

---

## 8. Discourse Profiles & CLI Output

- **Module:** `v4/dialogue_pipeline.py` (`format_dialogue_report`)

The human‑readable v4 report includes:

- Header with **turn count** and **speaker list**.
- **Contradiction Matrix** summary per speaker pair.
- **Evasion Scorer**:
  - Aggregate score.
  - Top evasive answers and their reasons.
- **Power Dynamics** per speaker (dominance, authority, turns, interruptions).
- **Topic Threading** summary (if available).
- **Discourse Profile**:
  - Combines:
    - Per‑speaker dominance.
    - Average evasion score (via `DialogueEvasionAnalyzer`).
    - Fallacy “habits” per speaker (using `LogicalFallacyAnalyzer` on each turn).
  - Assigns high‑level tactics such as:
    - “Fact-based / Questioning”
    - “Dominant”
    - “Evasion”
    - “Evasion / Redefinition”

This yields a compact **tactical signature** per speaker.

---

## 9. CLI & JSON Integration

From `src/discourse_engine/__main__.py`:

- `--dialogue`
  - Parses speaker‑tagged transcripts from stdin/args.
  - Runs v4 dialogue analysis in addition to the main v1/v2 report.
  - Prints a textual v4 summary (`format_dialogue_report`).

- `--dialogue-json PATH`
  - Runs the same analysis.
  - Exports a JSON structure via `dialogue_report_to_dict` and writes it to `PATH`.

Programmatic usage:

```python
from discourse_engine import (
    parse_speaker_tagged_text,
    run_dialogue_analysis,
    format_dialogue_report,
)

text = """
Interviewer: Why did you approve the $500 million transfer?
Politician: We need to focus on the jobs this created.
"""

dialogue = parse_speaker_tagged_text(text)
report = run_dialogue_analysis(dialogue.turns)
print(format_dialogue_report(report))
```

v4 thereby provides the **dialogue analysis layer** that v5 later reuses for scene detection, social graph stubs, and library‑mode discourse maps.

