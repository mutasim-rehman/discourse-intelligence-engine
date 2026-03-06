## Discourse Intelligence Engine V6 – Unified CLI, Library Intelligence, and Character Arcs

V6 turns the engine from a **single‑shot analyzer** into a **multi‑document intelligence system** with:

- A **unified CLI** (`discourse-engine analyze`) for text, files, folders, and YouTube.
- A **Library Persona Engine** that aggregates behaviors across many documents.
- A **Character Arc layer** that models how speakers evolve over time (within and across texts).

V6 is designed as a thin orchestration layer on top of the existing v3/v4/v5 engines.

---

### 1. High‑Level Architecture

```text
src/discourse_engine/
├── __main__.py            # CLI entry: defines subcommands (starting with `analyze`)
├── main.py                # v1–v3 snapshot pipeline (Report + formatting)
├── v4/                    # Dialogue-level analysis (turns, power, evasion, topics)
├── v5/                    # DiscourseMap graph, scenes, library mode, mermaid export
└── v6/
    ├── cli.py             # V6 unified CLI: `discourse-engine analyze ...`
    ├── aggregator.py      # Library Persona Engine (library_report.json)
    ├── arcs.py            # Character/relationship arc data models
    └── arcs_pipeline.py   # Arc construction (single doc + library)
```

**Pillar A – Analysis (Snapshot)** still lives primarily in `main.py`, `v4`, and `v5`.

**Pillar B – Temporal Arcs (Timeline)** is implemented in `v6/arcs.py` and `v6/arcs_pipeline.py`, with CLI wiring in `v6/cli.py`.

---

### 2. Unified CLI (`discourse-engine analyze`)

- **Module**: `src/discourse_engine/v6/cli.py`
- **Entry**: `discourse-engine` console script → `discourse_engine.__main__:main()` → `add_analyze_subparser(...)` → `run_analyze_from_args(...)`.

Supported inputs:

- **Raw text**:
  - `discourse-engine analyze "Your text here..." [flags]`
- **Files**:
  - `discourse-engine analyze path/to/file.txt [flags]`
- **YouTube**:
  - `discourse-engine analyze --youtube VIDEO_ID [flags]`
- **Batch folders**:
  - `discourse-engine analyze ./folder --batch [flags]`

Key flags:

- `--export` – export a V5 map JSON to `exports/` with an auto‑generated name and a sidecar Mermaid `.mmd`.
- `--v5-map-json PATH` – explicit V5 map JSON path.
- `--dialogue`, `--dialogue-json PATH` – v4 dialogue outputs.
- `--v3`, `--export-viz PATH` – v3 narrative arc outputs.
- `--v6-arcs-json PATH` – export **V6 character/relationship arcs** for this run (document or batch).
- Batch‑only:
  - `--batch` – treat `target` as a folder; build a library map.
  - `--library-report-json PATH` – cross‑document persona summary (Library Persona Engine).

The `run_analyze_from_args` flow:

1. Resolve input: YouTube → file → text → stdin → interactive.
2. Call `run_single_document(...)` **or** `run_batch_analyze(...)` depending on `--batch`.
3. Always run the v1–v3 snapshot pipeline (`run_pipeline`) and print the human‑readable report.
4. Optionally:
   - Run v3 narrative arc.
   - Run v4 dialogue pipeline for richer fallacies, evasion, topics, and JSON.
   - Build a V5 `DiscourseMap` and export JSON + `.mmd`.
   - Build and export V6 arc JSON (`--v6-arcs-json`).

---

### 3. Library Persona Engine (`v6/aggregator.py` + `v5/library.py`)

**Goal**: create a **Global Speaker Registry** across many documents, with:

- Median evasion scores.
- Top fallacies.
- Coarse tactical signatures (coercive/defensive/fact‑based turns).

Pipeline:

1. **Batch mode** (`--batch`) uses:
   - `v6/cli.py::run_batch_analyze(folder, args)` to:
     - Walk all files in a folder.
     - Build a combined V5 `DiscourseMap` via `v5/library.build_library_map`.
2. **`build_library_map`**:
   - For each `(document_id, text)`:
     - Runs `build_v5_discourse_map` (scene detection + social graph).
     - If dialogue‑heavy, runs the v4 dialogue pipeline to refine:
       - Evasion per speaker.
       - Fallacy counts per speaker.
       - Coercive/defensive/fact‑based turn tallies.
   - Aggregates everything into one `DiscourseMap`:
     - `character_profiles[character_id]` with:
       - `documents` list.
       - `coercive_turns`, `defensive_turns`, `fact_based_turns`.
       - `metadata["fallacy_habits"]`, `metadata["evasion_scores"]`, `metadata["evasion_by_document"]`, `metadata["fallacy_counts"]`.
3. **`v6/aggregator.py`**:
   - `build_library_persona_report(dm)`:
     - Computes per‑speaker:
       - Median evasion.
       - Top 3 fallacies (by total count).
       - Evasion by document.
     - Returns `{"speakers": { ... }, "documents": [...]}`.
   - `export_library_persona_report(dm, path)`:
     - Writes `library_report.json` for dashboards or auditing.

CLI:

- `discourse-engine analyze ./folder --batch --v5-map-json master_graph.json --library-report-json library_report.json`

This produces:

- `master_graph.json` – V5 library map.
- `master_graph.mmd` – library‑level social graph (when `--export` is used).
- `library_report.json` – cross‑document persona statistics.

---

### 4. Character & Relationship Arcs (`v6/arcs.py`, `v6/arcs_pipeline.py`)

**Goal**: model **how** speakers evolve rather than just **what** they say at a point in time.

Core concepts:

- `CharacterArcPoint`:
  - One point on a character’s timeline.
  - Fields:
    - `document_id`
    - `scene_id` (optional)
    - `turn_index` (optional; None for segment‑level points)
    - `position` in \([0,1]\) across the text.
    - `metrics` dict (authority, evasion, tactic, deltas, etc.).
- `CharacterArc`:
  - `character_id`, `display_name`
  - `points: list[CharacterArcPoint]`
  - `events: list[ArcEvent]` (power pivots, evasion spikes, tactic shifts, etc.).
- `RelationshipArc`:
  - Tracks pairwise interactions (`responds_to`, `aligns_with`, `follows`) over time.

#### 4.1 Single‑document arcs

- **Entry**: `build_character_arcs(dm: DiscourseMap, dialogue_report: DialogueReport | None, document_id: str | None)`

Steps:

1. **Align to dialogue**:
   - From v4 `DialogueReport`:
     - Get all turns, power dynamics, and evasion scores.
     - Run per‑turn fallacy analysis (`LogicalFallacyAnalyzer`) to count fallacies per type.
2. **Segment the dialogue**:
   - Divide turns into up to `N = 10` sequential segments.
   - For each segment and speaker:
     - Aggregate:
       - Average dominance and authority.
       - Average evasion across answers.
       - Fallacy counts per type.
     - Choose a **dominant tactic label** (e.g., `straw_man`, `appeal_to_fear`, or `Fact-based` if none).
   - Create a `CharacterArcPoint` per speaker/segment with:
     - `position` ≈ midpoint of the segment (normalized 0–1).
     - `metrics`:
       - `segment_index`
       - `dominance_score`, `authority_score`
       - `evasion_score`
       - `tactic_label`
3. **Velocity metrics and turning points**:
   - For each character’s segment series, compute deltas:
     - `authority_delta`: change vs previous segment.
     - `evasion_delta`: change vs previous segment.
     - `tactic_changed_from`: previous dominant tactic if it changed.
   - Across all speakers and segments, detect:
     - **Power pivots**:
       - When a speaker’s authority in a segment:
         - Becomes the segment leader, and
         - Exceeds that speaker’s previous best by ≥ 0.2 and is ≥ 0.5.
       - Emits an `ArcEvent(label="power_pivot", details=...)`.
     - **Evasion spikes** (transparency turning points):
       - When `evasion_score ≥ 0.8` and `evasion_delta ≥ 0.2`.
       - Emits an `ArcEvent(label="evasion_spike", details=...)`.
4. **Library persona enrichment**:
   - Merge in coarse library‑level tactical signatures from `character_profiles`:
     - `tactical_signature_summary` event with coercive/defensive/fact‑based counts.
     - `library_evasion_profile` event with median evasion and sample size, when available.

#### 4.2 Relationship arcs

- **Entry**: `build_relationship_arcs(dm: DiscourseMap)`

Steps:

- Iterate v5 edges of kinds:
  - `responds_to` – Q→A or directed answer edges.
  - `aligns_with` – agreement edges.
  - `follows` – adjacency interactions.
- For each `(source_speaker, target_speaker)` pair:
  - Create/extend a `RelationshipArc` with points capturing:
    - `document_id`, `scene_id`, `turn_index` (if present).
    - Approximate `position` based on `turn_index`.
    - `metrics`: edge kind, `evasion_score` (when present), etc.

#### 4.3 Library‑level arcs

- **Entry**: `build_library_character_arcs(library_map: DiscourseMap)`

Steps:

- Treat each document in `library_map.metadata["documents"]` as a position on a global axis.
- For each character:
  - Add a `CharacterArcPoint` per document with:
    - `position` = normalized index of the document.
    - `metrics` including per‑document tactical signature and `fallacy_habits`.

The arcs layer is exported for frontends via `arcs_to_view_payload(...)` and the `--v6-arcs-json` CLI flag.

---

### 5. Exports & Frontend Contracts

V6 defines three primary JSON/Mermaid contracts that frontend dashboards can rely on:

- **`v5_map.json`** – DiscourseMap export:
  - `nodes`, `edges`, `scenes`, `character_profiles`, `metadata`.
  - Backed by `v5/models.py` and `v5/visualization.py`.
- **V6 arcs JSON** (`--v6-arcs-json`) – arc‑centric view:
  - Top‑level structure:
    - `characters[character_id] = { character_id, display_name, points, events }`
    - `relationships["A__B"] = { pair, points, events }`
  - Each point is a time‑series entry with metrics and deltas; events mark turning points.
- **Mermaid `.mmd`** – graph view:
  - Generated from V5 map + views via:
    - `v5/mermaid.discourse_map_to_mermaid`.
  - Nodes: speaker nodes.
  - Edges:
    - `Answers (evasion=...)`, `Responds`, `Aligns With`, or sparse co‑occurrence edges.

These contracts are kept stable so that a V6 frontend can:

- Render **snapshot reports** (text).
- Draw **interaction graphs** (Mermaid or graph libraries).
- Plot **character arcs** and **turning points** over time.

---

### 6. Performance and LLM Budgeting

V6 introduces:

- **Concurrent library analysis**:
  - `build_library_map` uses a `ThreadPoolExecutor` to process documents in parallel, improving throughput on large batches.
- **LLM context control** (when `--llm-enhance` is enabled):
  - `main._prepare_llm_text(...)` takes long inputs and constructs a **start + middle + end** excerpt before calling any LLM‑based enhancer.
  - This prevents extremely long inputs (e.g., full novels or long hearings) from exceeding LLM context limits while still giving the model representative coverage.

These changes keep the V6 engine responsive for:

- Single long documents.
- Libraries of many shorter documents.
- Optional LLM‑enhanced runs without excessive token usage.

