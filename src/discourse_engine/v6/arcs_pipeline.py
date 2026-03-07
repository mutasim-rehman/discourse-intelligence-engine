"""V6 character arc construction pipeline.

Bridges:
- v4 DialogueReport (turn-level metrics, power dynamics, evasion)
- v5 DiscourseMap (scenes, speaker nodes, interaction edges)
into:
- CharacterArc and RelationshipArc series suitable for dashboards.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

from discourse_engine.analyzers.logical_fallacy import LogicalFallacyAnalyzer
from discourse_engine.v4.dialogue_pipeline import dialogue_from_turns
from discourse_engine.v4.models import DialogueReport
from discourse_engine.v4.power_dynamics import PowerDynamicsAnalyzer
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

    This builds a coarse, segment-based arc for each character, capturing:
    - Authority / dominance trajectory across the dialogue.
    - Evasion trajectory (how evasive recent answers are).
    - Tactic migration via dominant fallacy family per segment.
    """
    document_id = document_id or (
        dm.metadata.get("documents", [None])[0] if dm.metadata.get("documents") else None
    ) or "doc:0"

    arcs: Dict[str, CharacterArc] = {}

    # v4 dialogue alignment (if available)
    if dialogue_report is not None:
        dialogue = dialogue_report.dialogue
        turns = list(dialogue.turns)
        total_turns = len(turns)

        if total_turns:
            # --- Precompute per-turn metrics ---
            evasion_by_turn: dict[int, float] = {}
            if dialogue_report.evasion and dialogue_report.evasion.scores:
                for s in dialogue_report.evasion.scores:
                    evasion_by_turn[int(s.turn_index)] = float(s.score)

            fallacy_analyzer = LogicalFallacyAnalyzer()
            fallacies_by_turn: dict[int, Dict[str, int]] = {}
            for t in turns:
                if not t.text:
                    continue
                counts: Dict[str, int] = {}
                for f in fallacy_analyzer.analyze(t.text):
                    ftype = f.fallacy_type or f.name
                    counts[ftype] = counts.get(ftype, 0) + 1
                if counts:
                    fallacies_by_turn[t.turn_index] = counts

            # --- Segment the dialogue into N segments (path over time) ---
            max_segments = 10
            n_segments = min(max_segments, total_turns) or 1
            seg_size = max(1, total_turns // n_segments)
            power_analyzer = PowerDynamicsAnalyzer()

            # For each segment and speaker, aggregate metrics.
            per_speaker_segments: Dict[str, list[CharacterArcPoint]] = {}

            for seg_idx in range(n_segments):
                start = seg_idx * seg_size
                # Last segment takes the remainder.
                end = total_turns if seg_idx == n_segments - 1 else min(
                    total_turns, (seg_idx + 1) * seg_size
                )
                if start >= end:
                    continue

                segment_turns = turns[start:end]
                segment_pos = _normalized_position_from_turn(
                    (start + end - 1) // 2, total_turns
                )

                # Segment-local authority/dominance: compute from ONLY this segment's turns.
                power_in_segment: Dict[str, tuple[float, float]] = {}
                try:
                    segment_dialogue = dialogue_from_turns(segment_turns)
                    segment_power = power_analyzer.analyze(segment_dialogue)
                    for m in segment_power.speakers:
                        power_in_segment[m.speaker_id] = (
                            float(m.dominance_score),
                            float(m.authority_score),
                        )
                except Exception:
                    pass

                # Aggregate metrics per speaker within this segment.
                per_speaker_data: Dict[str, Dict[str, Any]] = {}
                for t in segment_turns:
                    sid = t.speaker_id
                    if not sid:
                        continue
                    data = per_speaker_data.setdefault(
                        sid,
                        {
                            "dom_sum": 0.0,
                            "auth_sum": 0.0,
                            "count": 0,
                            "evasion_sum": 0.0,
                            "evasion_count": 0,
                            "fallacy_counts": {},
                        },
                    )
                    dom, auth = power_in_segment.get(sid, (0.0, 0.0))
                    data["dom_sum"] += dom
                    data["auth_sum"] += auth
                    data["count"] += 1
                    if t.turn_index in evasion_by_turn:
                        data["evasion_sum"] += evasion_by_turn[t.turn_index]
                        data["evasion_count"] += 1
                    if t.turn_index in fallacies_by_turn:
                        for ftype, c in fallacies_by_turn[t.turn_index].items():
                            data["fallacy_counts"][ftype] = (
                                data["fallacy_counts"].get(ftype, 0) + c
                            )

                for sid, data in per_speaker_data.items():
                    arc = arcs.setdefault(
                        sid,
                        CharacterArc(
                            character_id=sid,
                            display_name=dialogue.speaker_profiles.get(sid).display_name
                            if sid in dialogue.speaker_profiles
                            else sid,
                        ),
                    )
                    count = max(1, data["count"])
                    seg_dom = data["dom_sum"] / count
                    seg_auth = data["auth_sum"] / count
                    if data["evasion_count"]:
                        seg_evasion = data["evasion_sum"] / data["evasion_count"]
                    else:
                        seg_evasion = 0.0

                    # Tactic: only assign fallacy label when segment has at least one fallacy hit.
                    fall_counts = data["fallacy_counts"]
                    tactic_label = "Fact-based"
                    if fall_counts:
                        dominant_ftype, dominant_count = max(
                            fall_counts.items(), key=lambda kv: kv[1]
                        )
                        if dominant_count > 0:
                            tactic_label = dominant_ftype

                    metrics = {
                        "segment_index": seg_idx,
                        "dominance_score": seg_dom,
                        "authority_score": seg_auth,
                        "evasion_score": seg_evasion,
                        "tactic_label": tactic_label,
                    }

                    pt = CharacterArcPoint(
                        document_id=document_id,
                        scene_id=None,
                        turn_index=None,
                        position=segment_pos,
                        metrics=metrics,
                    )
                    per_speaker_segments.setdefault(sid, []).append(pt)

            # Attach segment points and compute velocity metrics + turning points.
            # We need cross-speaker visibility for power pivots.
            for sid, points in per_speaker_segments.items():
                # Sort by position to ensure consistent deltas.
                points.sort(key=lambda p: p.position)
                prev_auth = None
                prev_evasion = None
                prev_tactic = None
                for p in points:
                    auth = float(p.metrics.get("authority_score", 0.0))
                    ev = float(p.metrics.get("evasion_score", 0.0))
                    tactic = str(p.metrics.get("tactic_label", "Fact-based"))
                    if prev_auth is not None:
                        p.metrics["authority_delta"] = auth - prev_auth
                    else:
                        p.metrics["authority_delta"] = 0.0
                    if prev_evasion is not None:
                        p.metrics["evasion_delta"] = ev - prev_evasion
                    else:
                        p.metrics["evasion_delta"] = 0.0
                    if prev_tactic is not None and tactic != prev_tactic:
                        p.metrics["tactic_changed_from"] = prev_tactic
                    prev_auth = auth
                    prev_evasion = ev
                    prev_tactic = tactic

                arc = arcs.setdefault(
                    sid,
                    CharacterArc(
                        character_id=sid,
                        display_name=dialogue.speaker_profiles.get(sid).display_name
                        if sid in dialogue.speaker_profiles
                        else sid,
                    ),
                )
                arc.points.extend(points)

            # Slope-based turning points: authority shift, tactic change, power pivot, evasion spike.
            # 1) Per-speaker: fire event when |authority_delta| >= 0.15 or tactic changes.
            for sid, points in per_speaker_segments.items():
                points.sort(key=lambda p: p.position)
                for p in points:
                    auth_delta = float(p.metrics.get("authority_delta", 0.0))
                    tactic_from = p.metrics.get("tactic_changed_from")
                    if abs(auth_delta) >= 0.15:
                        label = "authority_shift_up" if auth_delta > 0 else "authority_shift_down"
                        arcs[sid].events.append(
                            ArcEvent(
                                position=p.position,
                                label=label,
                                details={
                                    "segment_index": p.metrics.get("segment_index"),
                                    "authority_delta": auth_delta,
                                    "authority_score": p.metrics.get("authority_score"),
                                },
                            )
                        )
                    if tactic_from is not None:
                        arcs[sid].events.append(
                            ArcEvent(
                                position=p.position,
                                label="tactic_shift",
                                details={
                                    "segment_index": p.metrics.get("segment_index"),
                                    "from": tactic_from,
                                    "to": p.metrics.get("tactic_label"),
                                },
                            )
                        )

            # 2) Cross-speaker: power pivot (leader change) and evasion spike.
            segments_by_idx: Dict[int, Dict[str, CharacterArcPoint]] = {}
            for sid, arc in arcs.items():
                for p in arc.points:
                    seg_idx = int(p.metrics.get("segment_index", -1))
                    if seg_idx >= 0:
                        segments_by_idx.setdefault(seg_idx, {})[sid] = p

            prev_leader_sid: str | None = None
            for seg_idx in sorted(segments_by_idx.keys()):
                seg_points = segments_by_idx[seg_idx]
                leader_sid = None
                leader_auth = 0.0
                for sid, p in seg_points.items():
                    a = float(p.metrics.get("authority_score", 0.0))
                    if leader_sid is None or a > leader_auth:
                        leader_sid, leader_auth = sid, a

                if leader_sid is not None and prev_leader_sid is not None and leader_sid != prev_leader_sid:
                    arcs[leader_sid].events.append(
                        ArcEvent(
                            position=seg_points[leader_sid].position,
                            label="power_pivot",
                            details={
                                "segment_index": seg_idx,
                                "authority": leader_auth,
                                "previous_leader": prev_leader_sid,
                            },
                        )
                    )
                prev_leader_sid = leader_sid

                for sid, p in seg_points.items():
                    ev = float(p.metrics.get("evasion_score", 0.0))
                    ev_delta = float(p.metrics.get("evasion_delta", 0.0))
                    if ev >= 0.6 and ev_delta >= 0.15:
                        arcs[sid].events.append(
                            ArcEvent(
                                position=p.position,
                                label="evasion_spike",
                                details={
                                    "segment_index": seg_idx,
                                    "evasion": ev,
                                    "evasion_delta": ev_delta,
                                },
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

