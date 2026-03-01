# Discourse Intelligence Engine v3
## Computational Rhetoric & Ideological Signal Modeling Framework

### Overview

v3 extends the discourse engine into a **research-grade computational rhetoric system** that models:

- **Discursive power** — who controls framing, escalation, and narrative
- **Moral structure** — foundation activation across time and speakers
- **Strategic framing** — reframing, evasion, certainty inflation
- **Narrative control** — arc, drift, and influence visualization

---

## Module Architecture

```
discourse_engine/
├── analyzers/           # Existing: fallacy, assumptions, agenda, satire, etc.
├── v3/
│   ├── narrative_arc/   # Narrative Arc & Power Dynamics Modeling
│   ├── contradiction/   # Cross-Speaker Contradiction Detection
│   ├── temporal_drift/  # Temporal Rhetoric Drift Tracking
│   └── debate_heatmap/  # Debate Heatmap & Influence Visualization
└── models/
    └── v3_models.py     # Shared v3 data structures
```

---

## 1. Narrative Arc & Power Dynamics Modeling

### Purpose
Model rhetorical evolution across time within a single text (speech, script, interview).

### Input
- Single document (or transcript)
- Optional: chunk size (default: 5 sentences)

### Per-Chunk Metrics
| Metric | Source |
|--------|--------|
| Emotional intensity | Tone analyzer + intensifier density |
| Fear / Authority / Identity | Trigger profile lexicons |
| Pronoun distribution | we/they, I/you ratios |
| Modal density | must, will, can, etc. |
| Threat score | Fear term density + escalation markers |
| Agency framing | Passive vs active voice ratio |

### Output
- **Time series**: `[(chunk_idx, position_0_1, metrics_dict), ...]`
- **Visualization data**: JSON for charting (x=progression, y=intensity, overlays=spikes)
- **Arc summary**: Escalation points, dominant framing shifts, peak intensity regions

### Extension Points
- Moral foundation activation per chunk (requires MFT lexicon)
- Embedding-based coherence across chunks

---

## 2. Cross-Speaker Contradiction Detection

### Purpose
Detect contradictions, reframing, and evasion between speakers (debates, interviews).

### Input
- Speaker-segmented transcript: `[(speaker_id, text), ...]`
- Optional: claim extraction (manual or NLI-based)

### Detection Types
| Type | Method |
|------|--------|
| Direct contradiction | Negation + semantic overlap, or NLI (entailment/contradiction) |
| Reframing | Topic shift, term substitution, scope narrowing |
| Strategic ambiguity | Hedging density, vague referents |
| Question avoidance | Question→non-answer pair detection |

### Output
```
ContradictionReport:
  - pairs: [(speaker_a, text_a, speaker_b, text_b, probability, type)]
  - reframing_detected: bool
  - evasion_likelihood: float
  - summary: str
```

### Extension Points
- NLI model plug-in (e.g. deberta-base-mnli, bart-mnli)
- Claim extraction pipeline

---

## 3. Temporal Rhetoric Drift Tracking

### Purpose
Track how a speaker's rhetorical positioning shifts across multiple speeches over time.

### Input
- Multiple documents with metadata: `[(date, text), ...]`
- Same speaker assumed

### Per-Document Metrics
- Lexicon-based: fear, authority, identity, liberty (from trigger + moral lexicons)
- Embedding-based (optional): Ideological vector per document
- Moral foundation profile

### Output
- **Drift vectors**: Change in each dimension between consecutive documents
- **Timeline plot data**: date → (fear, authority, liberty, ...) for 2D/3D viz
- **Shift summary**: "Authority framing increased 40% from speech 1 to 3"

### Extension Points
- Sentence-transformers for embedding-based drift
- Reference corpus comparison (conservative/progressive anchors)

---

## 4. Debate Heatmap & Influence Visualization

### Purpose
Visualize emotional intensity, dominance, and control dynamics across speaker turns.

### Input
- Speaker turns: `[(speaker_id, turn_idx, text, start_time?, end_time?), ...]`

### Per-Turn Metrics
| Metric | Method |
|--------|--------|
| Emotional intensity | Tone + intensifier count |
| Dominance language | Imperatives, declaratives, certainty markers |
| Certainty inflation | Modal verb profile |
| Interruption markers | Incomplete sentences, overlap cues (if timestamps) |

### Output
- **Heatmap grid**: `rows=speakers, cols=time_bins, values=intensity`
- **Influence scores**: Per-turn and rolling
- **Escalation timeline**: Who escalated when
- **JSON export**: For D3, matplotlib, or custom viz

---

## Data Flow

```
                    ┌─────────────────────┐
                    │  Raw Input          │
                    │  (text, transcript, │
                    │   multi-doc)        │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │ Narrative Arc│    │ Contradiction│    │ Temporal     │
   │ (single doc) │    │ (multi-turn) │    │ Drift        │
   └──────┬───────┘    └──────┬───────┘    │ (multi-doc)  │
          │                   │            └──────┬───────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Debate Heatmap     │
                    │  (turn-segmented)   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Unified Report     │
                    │  + Viz Data (JSON)  │
                    └─────────────────────┘
```

---

## Usage

### CLI
```bash
discourse-engine "Your text..." --v3                    # Add Narrative Arc
discourse-engine -y VIDEO_ID --v3 --export-viz out.json # Export viz data
```

### Python API
```python
from discourse_engine.v3 import NarrativeArcAnalyzer, ContradictionAnalyzer, TemporalDriftAnalyzer, DebateHeatmapAnalyzer

arc = NarrativeArcAnalyzer(chunk_size=5).analyze(text)
contra = ContradictionAnalyzer().analyze([("A", text_a), ("B", text_b)])
drift = TemporalDriftAnalyzer().analyze([("id1", "date", text1), ...])
heatmap = DebateHeatmapAnalyzer().analyze([("Alice", turn1), ("Bob", turn2)])
```

---

## Dependencies

### Core (no new deps)
- Narrative Arc: Uses existing analyzers
- Contradiction: Heuristic (negation, keywords)
- Drift: Lexicon-based
- Heatmap: Uses existing analyzers

### Optional (for research-grade)
- `transformers` + NLI model: Contradiction detection
- `sentence-transformers`: Ideological embeddings, drift
- `matplotlib` / `plotly`: Built-in visualization

---

## Academic Framing

**Full name**: *Computational Rhetoric & Ideological Signal Modeling Framework*

**Positioning**:
- Models discursive power structures
- Extracts moral foundation activation
- Tracks strategic framing and narrative control
- Produces interpretable, visualizable outputs for qualitative research

**Use cases**:
- Political speech analysis
- Media discourse studies
- Debate forensics
- Fiction/narrative structure analysis
- Interview and oral history research
