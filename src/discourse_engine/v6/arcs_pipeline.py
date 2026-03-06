"""V6 character arc construction pipeline.

Bridges:
- v4 DialogueReport (turn-level metrics, power dynamics, evasion)
- v5 DiscourseMap (scenes, speaker nodes, interaction edges)
into:
- CharacterArc and RelationshipArc series suitable for dashboards.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

from discourse_engine.v4.models import DialogueReport
from discourse_engine.v5.models import DiscourseMap, GraphEdge
from discourse_engine.v6.arcs import (
    ArcEvent,
    CharacterArc,
    CharacterArcPoint,
    RelationshipArc,
    RelationshipArcPoint,
)


def _normalized_position_from_turn(turn_index: int, total_turns: int) -> float:
    if total_turns <= 1:
        return 0.0
    return max(0.0, min(1.0, turn_index / (total_turns - 1)))


def build_character_arcs(
    dm: DiscourseMap,
    dialogue_report: DialogueReport | None = None,
    document_id: str | None = None,
) -> Dict[str, CharacterArc]:
    """Build per-character arcs for a single document.

    For now this is deliberately simple:
    - position axis = normalized turn index within the dialogue (when available).
    - metrics per point = authority/dominance (v4 power), evasion (v4),
      basic fallacy habit counts and semantic drift snapshots (v5).
    """
    document_id = document_id or (
        dm.metadata.get("documents", [None])[0] if dm.metadata.get("documents") else None
    ) or "doc:0"

    arcs: Dict[str, CharacterArc] = {}

    # v4 dialogue alignment (if available)
    turns = []
    evasion_by_turn: dict[int, float] = {}
    if dialogue_report is not None:
        dialogue = dialogue_report.dialogue
        turns = list(dialogue.turns)
        total_turns = len(turns)

        if dialogue_report.evasion and dialogue_report.evasion.scores:
            for s in dialogue_report.evasion.scores:
                evasion_by_turn[int(s.turn_index)] = float(s.score)

        power_by_speaker: dict[str, tuple[float, float]] = {}
        if dialogue_report.power_dynamics:
            for m in dialogue_report.power_dynamics.speakers:
                power_by_speaker[m.speaker_id] = (
                    float(m.dominance_score),
                    float(m.authority_score),
                )
        else:
            power_by_speaker = {}

        # Build an initial arc point for each turn.
        for t in turns:
            sid = t.speaker_id
            if not sid:
                continue
            arc = arcs.setdefault(
                sid,
                CharacterArc(
                    character_id=sid,
                    display_name=dialogue.speaker_profiles.get(sid).display_name
                    if sid in dialogue.speaker_profiles
                    else sid,
                ),
            )
            pos = _normalized_position_from_turn(t.turn_index, total_turns)
            dom, auth = power_by_speaker.get(sid, (0.0, 0.0))
            metrics = {
                "dominance_score": dom,
                "authority_score": auth,
            }
            if t.turn_index in evasion_by_turn:
                metrics["evasion_score"] = evasion_by_turn[t.turn_index]

            arc.points.append(
                CharacterArcPoint(
                    document_id=document_id,
                    scene_id=None,
                    turn_index=t.turn_index,
                    position=pos,
                    metrics=metrics,
                )
            )

    # Enrich with v5 library-level metadata when present (fallacy habits, docs).
    for cid, profile in dm.character_profiles.items():
        arc = arcs.setdefault(
            cid,
            CharacterArc(
                character_id=cid,
                display_name=profile.display_name or cid,
            ),
        )
        # Attach coarse tactical signature summary as a single event.
        if (
            profile.coercive_turns
            or profile.defensive_turns
            or profile.fact_based_turns
        ):
            arc.events.append(
                ArcEvent(
                    position=0.5,
                    label="tactical_signature_summary",
                    details={
                        "coercive_turns": profile.coercive_turns,
                        "defensive_turns": profile.defensive_turns,
                        "fact_based_turns": profile.fact_based_turns,
                    },
                )
            )

        # Library Persona additions (if present).
        meta = profile.metadata or {}
        ev_scores = meta.get("evasion_scores")
        if isinstance(ev_scores, Iterable):
            ev_list = [float(x) for x in ev_scores if isinstance(x, (int, float))]
            if ev_list:
                arc.events.append(
                    ArcEvent(
                        position=0.6,
                        label="library_evasion_profile",
                        details={
                            "median_evasion": sorted(ev_list)[len(ev_list) // 2],
                            "samples": len(ev_list),
                        },
                    )
                )

    return arcs


def build_relationship_arcs(dm: DiscourseMap) -> Dict[Tuple[str, str], RelationshipArc]:
    """Derive simple relationship arcs based on interaction edges.

    For now we aggregate:
    - responds_to: answer links between speakers (directional).
    - aligns_with: agreement edges.
    """
    rel_arcs: Dict[Tuple[str, str], RelationshipArc] = {}

    # Precompute document_id from metadata when available.
    document_id = (dm.metadata.get("documents") or [None])[0] or "doc:0"

    for edge in dm.edges:
        if edge.kind not in {"responds_to", "aligns_with", "follows"}:
            continue
        if not edge.source.startswith("speaker:") or not edge.target.startswith(
            "speaker:"
        ):
            continue

        a = edge.source.split(":", 1)[1]
        b = edge.target.split(":", 1)[1]
        key = (a, b)
        arc = rel_arcs.setdefault(key, RelationshipArc(pair=key))

        meta = edge.metadata or {}
        turn_index = meta.get("turn_index")
        scene_id = meta.get("scene_id")

        # Position: approximate via turn index if present, else 0.5.
        position = 0.5
        if isinstance(turn_index, int):
            # We do not know total turns here; dashboards can normalize per doc.
            position = max(0.0, min(1.0, float(turn_index) / 100.0))

        metrics: dict[str, Any] = {"kind": edge.kind}
        if "evasion_score" in meta:
            metrics["evasion_score"] = meta["evasion_score"]

        arc.points.append(
            RelationshipArcPoint(
                document_id=document_id,
                scene_id=scene_id,
                turn_index=turn_index if isinstance(turn_index, int) else None,
                position=position,
                metrics=metrics,
            )
        )

    return rel_arcs


def build_library_character_arcs(library_map: DiscourseMap) -> Dict[str, CharacterArc]:
    """Very coarse library-level arcs using DiscourseMap character profiles.

    This is intentionally minimal: it treats each document mention as a point on
    a timeline and attaches aggregate metadata (e.g., fallacy habits).
    """
    arcs: Dict[str, CharacterArc] = {}

    documents = library_map.metadata.get("documents") or []
    doc_positions = {
        doc_id: (i / (len(documents) - 1) if len(documents) > 1 else 0.0)
        for i, doc_id in enumerate(documents)
    }

    for cid, profile in library_map.character_profiles.items():
        arc = arcs.setdefault(
            cid,
            CharacterArc(
                character_id=cid,
                display_name=profile.display_name or cid,
            ),
        )
        for doc_id in profile.documents:
            pos = doc_positions.get(doc_id, 0.0)
            arc.points.append(
                CharacterArcPoint(
                    document_id=doc_id,
                    scene_id=None,
                    turn_index=None,
                    position=pos,
                    metrics={
                        "coercive_turns": profile.coercive_turns,
                        "defensive_turns": profile.defensive_turns,
                        "fact_based_turns": profile.fact_based_turns,
                        "fallacy_habits": profile.metadata.get("fallacy_habits", []),
                    },
                )
            )

    return arcs

