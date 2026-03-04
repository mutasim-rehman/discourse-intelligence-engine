## Discourse Intelligence Engine V5 – Implementation Priorities

This document translates the high-level V5 feature plan into concrete implementation phases for the first pass.

### Scope of the First Implementation Pass

- **In-scope (Phase 1 / this pass)**
  - **Scene & conversation intelligence**
    - Unified entry point that runs a **scene detector** on every input and decides whether to:
      - Treat the text as primarily **narrative/monologue**, or
      - Treat it as **multi-speaker dialogue** (and run the v4 dialogue analyzers).
    - Lightweight **scene segmentation** and labeling (`scene_timeline` structure) with:
      - Start/end sentence indices.
      - Scene type label (e.g., `narrative`, `dialogue`, `mixed`).
      - Dominant speakers (for dialogue scenes).
    - Basic **n-speaker diarization support** by reusing and generalizing v4 dialogue models.
  - **Unified semantic graph foundation**
    - A v5 data model that represents:
      - Documents, scenes, speakers/characters.
      - Turns/chunks.
      - Topics and simple discourse relations (e.g., who introduces a topic).
    - JSON-serializable graph export that will back visualizations and downstream tools.
  - **Topic ownership (first cut)**
    - Per-scene/per-speaker topic introduction counts and simple “topic ownership” metrics.
  - **Library mode (multi-document) – MVP**
    - Ability to pass **multiple documents** into a v5 entry point and compute:
      - Per-entity **persona summaries** (basic statistics over tactics and topics).
      - Per-document **tactical signature** summaries.
    - Export as a JSON structure that can later be used for deeper cross-document analysis.
  - **Discourse map export – MVP**
    - A `v5_disourse_map.json`-style structure (not a UI) that includes:
      - Nodes: documents, scenes, speakers, topics.
      - Edges: speaks_in, introduces_topic, responds_to_topic.
      - Basic scores (e.g., topic ownership per speaker).

- **Partially in-scope (scaffolding only)**
  - **Narrative POV / focalization labels**
    - Simple heuristics (1st vs 3rd person, narrator vs character focus) attached to scenes.
  - **Reliability / subtext hooks**
    - Data model fields and placeholder scores wired into the graph, but with minimal logic.
  - **Irony / incongruity integration**
    - Reuse existing satire/irony signals and expose them as attributes on scenes and turns.

- **Out-of-scope for the first pass (planned for later phases)**
  - Full **emotional arc tracking per character** across chapters and documents.
  - Rich **narratology layer** (detailed focalization, narrative distance taxonomy).
  - Advanced **social graph & alliance detection** (beyond simple agreement/disagreement counts).
  - Deep **inter-textual strategy evolution** and motif/theme mining.
  - UI-level **interactive visualizations** (HTML dashboards, front-end components).

### Phase Breakdown

- **Phase 1 – Core V5 Engine (this implementation)**
  - Implement v5 models for scenes, graph nodes/edges, and exports.
  - Implement a scene detector and basic scene segmentation.
  - Integrate v5 into the existing CLI entry point so every run produces:
    - The existing v1/v2 report.
    - Optional v3/v4 extras (when requested).
    - A v5 semantic graph / discourse map JSON export structure in memory.
  - Add a minimal **library mode** API that can take multiple documents and emit:
    - Persona summaries per entity.
    - Topic ownership and basic tactics per entity.

- **Phase 2 – Narrative & Library Enhancements**
  - Enrich POV/focalization, reliability, and emotional arcs.
  - Extend library mode with longitudinal change detection across time-ordered corpora.
  - Add more nuanced topic ownership and framing/reframing detection integrated into the graph.

- **Phase 3 – Pragmatics & Visualization**
  - Integrate expanded irony/incongruity, politeness, and hyperbole detectors.
  - Build user-facing Discourse Map visualizations (HTML/JS or notebook widgets) on top of the v5 graph format.

