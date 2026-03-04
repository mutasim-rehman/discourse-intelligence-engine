"""V5 Library Mode: cross-document aggregation of discourse profiles.

Given multiple documents, this module:
- Builds a unified `DiscourseMap` spanning all documents.
- Aggregates per-character tactical signatures across contexts.
"""

from __future__ import annotations

from typing import Iterable, Tuple

from discourse_engine.v4.dialogue_pipeline import run_dialogue_from_text
from discourse_engine.analyzers.logical_fallacy import LogicalFallacyAnalyzer
from discourse_engine.v5.models import DiscourseMap
from discourse_engine.v5.scene_detector import build_v5_discourse_map


def build_library_map(documents: Iterable[Tuple[str, str]]) -> DiscourseMap:
    """Aggregate discourse maps and character profiles across documents.

    Parameters
    ----------
    documents:
        Iterable of (document_id, text) pairs.
    """
    combined = DiscourseMap()

    for doc_id, text in documents:
        result = build_v5_discourse_map(text, document_id=doc_id)
        dm = result.discourse_map

        # Merge nodes (last write wins, but ids are stable per kind).
        for node_id, node in dm.nodes.items():
            if node_id not in combined.nodes:
                combined.add_node(node)

        # Merge edges by simple concatenation.
        for edge in dm.edges:
            combined.add_edge(edge)

        # Merge scenes.
        for scene in dm.scenes:
            combined.scenes.append(scene)

        # Merge character profiles.
        for cid, profile in dm.character_profiles.items():
            combined_profile = combined.get_or_create_character(cid, display_name=profile.display_name)
            # Merge documents.
            for d in profile.documents:
                if d not in combined_profile.documents:
                    combined_profile.documents.append(d)

        combined.metadata.setdefault("documents", [])
        if doc_id not in combined.metadata["documents"]:
            combined.metadata["documents"].append(doc_id)

        # When a document is dialogue-heavy, refine tactical signatures using v4.
        if result.is_dialogue_heavy:
            dialogue_report = run_dialogue_from_text(text)
            dialogue = dialogue_report.dialogue

            # Evasion scores per speaker (mirrors v4.format_dialogue_report logic).
            evasion_by_speaker: dict[str, list[float]] = {}
            if dialogue_report.evasion and dialogue_report.evasion.scores:
                for s in dialogue_report.evasion.scores:
                    if s.turn_index < len(dialogue.turns):
                        spk = dialogue.turns[s.turn_index].speaker_id
                        evasion_by_speaker.setdefault(spk, []).append(s.score)

            # Fallacy habits per speaker.
            fallacy_counts: dict[str, dict[str, int]] = {}
            for t in dialogue.turns:
                if not t.text:
                    continue
                for f in LogicalFallacyAnalyzer().analyze(t.text):
                    ftype = f.fallacy_type or f.name
                    bucket = fallacy_counts.setdefault(t.speaker_id, {})
                    bucket[ftype] = bucket.get(ftype, 0) + 1

            # Map v4 power metrics into coarse tactical signatures.
            if dialogue_report.power_dynamics:
                for m in dialogue_report.power_dynamics.speakers:
                    avg_evasion = 0.0
                    if m.speaker_id in evasion_by_speaker and evasion_by_speaker[m.speaker_id]:
                        scores = evasion_by_speaker[m.speaker_id]
                        avg_evasion = sum(scores) / len(scores)

                    profile = combined.get_or_create_character(m.speaker_id)
                    if doc_id not in profile.documents:
                        profile.documents.append(doc_id)

                    # Simple heuristic mapping:
                    # - High dominance and high evasion → coercive/strategic.
                    # - High dominance only → coercive.
                    # - High evasion only → defensive.
                    # - Otherwise → fact-based / neutral.
                    if m.dominance_score >= 0.5 and avg_evasion >= 0.5:
                        profile.coercive_turns += 1
                    elif m.dominance_score >= 0.5:
                        profile.coercive_turns += 1
                    elif avg_evasion >= 0.5:
                        profile.defensive_turns += 1
                    else:
                        profile.fact_based_turns += 1

                    # Track which speakers exhibit a consistent fallacy habit.
                    counts = fallacy_counts.get(m.speaker_id) or {}
                    if counts:
                        # This is intentionally simple: library mode just needs a signal.
                        habit_type, _habit_count = max(counts.items(), key=lambda kv: kv[1])
                        profile.metadata.setdefault("fallacy_habits", set())  # type: ignore[assignment]
                        profile.metadata["fallacy_habits"].add(habit_type)  # type: ignore[index]

    # Normalize any non-serializable structures in metadata (e.g., sets).
    for profile in combined.character_profiles.values():
        habits = profile.metadata.get("fallacy_habits")
        if isinstance(habits, set):
            profile.metadata["fallacy_habits"] = sorted(habits)

    return combined

