"""V5 scene detection and discourse map construction.

This module provides a unified entry for turning raw text into:
- A coarse `Scene` timeline (narrative vs dialogue vs mixed).
- An initial n-speaker social graph embedding based on v4 dialogue parsing.
- A `DiscourseMap` graph that downstream tools and visualizations can consume.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from discourse_engine.utils.text_utils import split_sentences
from discourse_engine.v3.narrative_arc import NarrativeArcAnalyzer
from discourse_engine.v4.dialogue_pipeline import parse_speaker_tagged_text
from discourse_engine.v4.models import Dialogue
from discourse_engine.v5.models import DiscourseMap, Scene, GraphEdge, GraphNode
from discourse_engine.v5.semantic_drift import compute_semantic_drift

# Agreement patterns: "I agree with [Name]", "[Name] is right", "You're right"
_AGREE_WITH_RE = re.compile(
    r"\bI\s+agree\s+with\s+(?:the\s+)?([A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*)*)\b",
    re.IGNORECASE,
)
_IS_RIGHT_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*)*)\s+is\s+right\b",
    re.IGNORECASE,
)
_YOURE_RIGHT_RE = re.compile(r"\byou['\u2019]?re\s+right\b", re.IGNORECASE)


def _label_to_speaker_id(dialogue: Dialogue) -> dict[str, str]:
    """Build map from display name (and 'the X', and first/last word) to speaker_id."""
    out: dict[str, str] = {}
    for sid, profile in dialogue.speaker_profiles.items():
        if not profile.display_name:
            continue
        name = profile.display_name.strip()
        if not name:
            continue
        key = name.lower()
        out[key] = sid
        out["the " + key] = sid
        words = key.split()
        if len(words) == 1:
            out[words[0]] = sid
        else:
            out[words[0]] = sid
            out[words[-1]] = sid
    return out


def _resolve_agreed_with(turn_text: str, label_to_id: dict[str, str]) -> Optional[str]:
    """Return speaker_id of the person this turn agrees with, or None."""
    m = _AGREE_WITH_RE.search(turn_text)
    if m:
        name = m.group(1).strip().lower()
        if name in label_to_id:
            return label_to_id[name]
        if "the " + name in label_to_id:
            return label_to_id["the " + name]
    m = _IS_RIGHT_RE.search(turn_text)
    if m:
        name = m.group(1).strip().lower()
        if name in label_to_id:
            return label_to_id[name]
    return None


def _add_agreement_edges(
    dm: DiscourseMap,
    dialogue: Dialogue,
    document_id: str,
) -> None:
    """Detect 'I agree with X' / 'X is right' / 'You're right' and add aligns_with edges."""
    label_to_id = _label_to_speaker_id(dialogue)
    if not label_to_id:
        return
    turns = dialogue.turns
    for i, turn in enumerate(turns):
        text = turn.text or ""
        speaker_id = turn.speaker_id or "speaker"
        agreed_with = _resolve_agreed_with(text, label_to_id)
        if agreed_with and agreed_with != speaker_id:
            dm.add_edge(
                GraphEdge(
                    source=f"speaker:{speaker_id}",
                    target=f"speaker:{agreed_with}",
                    kind="aligns_with",
                    weight=1.0,
                    metadata={"document_id": document_id, "turn_index": i},
                )
            )
        elif _YOURE_RIGHT_RE.search(text) and i > 0:
            prev_speaker = turns[i - 1].speaker_id or "speaker"
            if prev_speaker != speaker_id:
                dm.add_edge(
                    GraphEdge(
                        source=f"speaker:{speaker_id}",
                        target=f"speaker:{prev_speaker}",
                        kind="aligns_with",
                        weight=1.0,
                        metadata={"document_id": document_id, "turn_index": i, "cue": "you're right"},
                    )
                )


def _add_inconsistency_flags(dm: DiscourseMap, dialogue: Dialogue) -> None:
    """Flag when a speaker's claims contradict across turns (e.g. voluntary vs mandatory)."""
    CONTRADICTION_PAIRS = [
        (r"\bvoluntary\b", r"\bmandatory\b"),
        (r"\boptional\b", r"\brequired\b"),
        (r"\balways\b", r"\bnever\b"),
        (r"\ball\b", r"\bnone\b"),
        (r"\byes\b", r"\bno\b"),
        (r"\bagree\b", r"\bdisagree\b"),
        (r"\bapproved\b", r"\brejected\b"),
    ]
    by_speaker: dict[str, list[str]] = {}
    for t in dialogue.turns:
        by_speaker.setdefault(t.speaker_id or "speaker", []).append((t.text or "").lower())
    flags: list[dict] = []
    for speaker_id, texts in by_speaker.items():
        if len(texts) < 2:
            continue
        for (pat_a, pat_b) in CONTRADICTION_PAIRS:
            ra, rb = re.compile(pat_a, re.I), re.compile(pat_b, re.I)
            for i, ti in enumerate(texts):
                for j, tj in enumerate(texts):
                    if i >= j:
                        continue
                    if ra.search(ti) and rb.search(tj):
                        flags.append({
                            "speaker_id": speaker_id,
                            "turn_indices": [i, j],
                            "pattern": f"{pat_a!r} vs {pat_b!r}",
                        })
                        break
    if flags:
        dm.metadata.setdefault("inconsistency_flags", []).extend(flags)


@dataclass
class SceneDetectionResult:
    """Lightweight wrapper around the constructed discourse map."""

    discourse_map: DiscourseMap
    is_dialogue_heavy: bool


def _estimate_pov(sentences: List[str]) -> str:
    """Heuristic POV estimate based on pronoun distribution."""
    text = " ".join(sentences).lower()
    first_person = sum(text.count(p) for p in (" i ", " i'm ", " i've ", " my ", " me "))
    third_person = sum(text.count(p) for p in (" he ", " she ", " they ", " his ", " her ", " him ", " them "))
    if first_person > third_person * 1.2 and first_person >= 2:
        return "first_person"
    if third_person > first_person * 1.2 and third_person >= 2:
        return "third_person"
    return "mixed"


def _is_dialogue_like(text: str, sentences: List[str]) -> bool:
    """Detect whether the text structurally resembles dialogue."""
    if not text:
        return False
    # Fast path: explicit speaker tags or common interview roles.
    lowered = text.lower()
    if "interviewer:" in lowered or "politician:" in lowered:
        return True
    if ":" in text:
        # Lines starting with "Name:" are strong dialogue hints.
        dialogue_lines = 0
        total_lines = 0
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            total_lines += 1
            if ":" in stripped:
                before, _after = stripped.split(":", 1)
                if 1 <= len(before.split()) <= 3:
                    dialogue_lines += 1
        if total_lines and dialogue_lines / total_lines >= 0.3:
            return True
    # Quotation-density heuristic.
    if sentences:
        quote_sents = sum(1 for s in sentences if '"' in s or "“" in s or "”" in s)
        if quote_sents / len(sentences) >= 0.4:
            return True
    return False


def build_v5_discourse_map(text: str, document_id: str = "doc:0") -> SceneDetectionResult:
    """Construct a V5 `DiscourseMap` with a minimal scene timeline.

    For this first pass, we:
    - Treat the entire document as a single scene, but label it as narrative vs dialogue.
    - When dialogue-like, reuse v4's speaker parsing to build an n-speaker social stub.
    - When narrative-like, derive POV and emotional intensity from the v3 narrative arc.
    """
    dm = DiscourseMap()
    dm.add_node(GraphNode(id=document_id, kind="document", label=document_id))

    sentences = split_sentences(text)
    total_sentences = len(sentences)

    is_dialogue = _is_dialogue_like(text, sentences)

    # Default scene-type and POV.
    scene_type = "dialogue" if is_dialogue else "narrative"
    pov = _estimate_pov(sentences) if not is_dialogue else "mixed"

    # Narrative arc-derived emotional signal (single scalar for now).
    emotional_intensity = 0.0
    if not is_dialogue and text.strip():
        arc = NarrativeArcAnalyzer().analyze(text)
        if arc.chunks:
            emotional_intensity = sum(c.emotional_intensity for c in arc.chunks) / len(arc.chunks)

    # Optional semantic drift summary between early and late segments.
    drift = compute_semantic_drift(text)
    if drift:
        dm.metadata["semantic_drift"] = drift

    scene_id = f"scene:{document_id}:0"
    scene = Scene(
        id=scene_id,
        document_id=document_id,
        index=0,
        sentence_start=0,
        sentence_end=total_sentences,
        scene_type=scene_type,
        pov=pov,
        focalizer="narrator",
        emotional_intensity=emotional_intensity,
    )

    # Attach scene to document in the graph.
    dm.add_scene(scene)
    dm.add_edge(
        GraphEdge(
            source=scene.id,
            target=document_id,
            kind="scene_in_document",
        )
    )

    # If dialogue-like, attempt n-speaker diarization and social stubs.
    if is_dialogue:
        dialogue = parse_speaker_tagged_text(text)
        turn_counts: dict[str, int] = {}

        for idx, turn in enumerate(dialogue.turns):
            speaker_id = turn.speaker_id or "speaker"
            display_name: Optional[str] = turn.display_name or speaker_id

            profile = dm.get_or_create_character(speaker_id, display_name=display_name)
            if document_id not in profile.documents:
                profile.documents.append(document_id)

            turn_counts[speaker_id] = turn_counts.get(speaker_id, 0) + 1

            turn_node_id = f"turn:{document_id}:{idx}"
            dm.add_node(
                GraphNode(
                    id=turn_node_id,
                    kind="turn",
                    label=f"{speaker_id}#{idx}",
                    metadata={
                        "speaker_id": speaker_id,
                        "turn_index": idx,
                    },
                )
            )
            # Turn participates in the scene and is spoken by the speaker.
            dm.add_edge(GraphEdge(source=turn_node_id, target=scene.id, kind="turn_in_scene"))
            dm.add_edge(
                GraphEdge(
                    source=f"speaker:{speaker_id}",
                    target=turn_node_id,
                    kind="speaks_in",
                )
            )

        # Compute dominant speakers and add simple social edges.
        if turn_counts:
            sorted_speakers = sorted(turn_counts.items(), key=lambda kv: kv[1], reverse=True)
            scene.dominant_speakers = [spk for spk, _count in sorted_speakers]
            # Mirror update into the stored scene node metadata.
            dm.nodes[scene.id].metadata["dominant_speakers"] = scene.dominant_speakers

            # Social graph stubs: undirected edges weighted by co-participation.
            speakers = [spk for spk, _ in sorted_speakers]
            for i, a in enumerate(speakers):
                for b in speakers[i + 1 :]:
                    weight = (turn_counts.get(a, 0) + turn_counts.get(b, 0)) / max(
                        len(dialogue.turns), 1
                    )
                    dm.add_edge(
                        GraphEdge(
                            source=f"speaker:{a}",
                            target=f"speaker:{b}",
                            kind="co_occurs_in_scene",
                            weight=weight,
                            metadata={"scene_id": scene.id},
                        )
                    )

            _add_agreement_edges(dm, dialogue, document_id)
            _add_inconsistency_flags(dm, dialogue)

    dm.metadata.setdefault("documents", []).append(document_id)
    dm.metadata.setdefault("scene_timeline", []).append(
        {
            "scene_id": scene.id,
            "document_id": document_id,
            "index": scene.index,
            "sentence_start": scene.sentence_start,
            "sentence_end": scene.sentence_end,
            "scene_type": scene.scene_type,
            "pov": scene.pov,
            "dominant_speakers": scene.dominant_speakers,
        }
    )

    return SceneDetectionResult(discourse_map=dm, is_dialogue_heavy=is_dialogue)

