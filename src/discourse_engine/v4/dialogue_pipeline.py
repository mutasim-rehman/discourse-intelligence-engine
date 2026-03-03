"""v4 dialogue pipeline and text-format parsing utilities.

This module provides:
- Minimal data ingestion helpers for speaker-tagged transcripts.
- A future hook (`run_dialogue_analysis`) for full v4 analysis over DialogueTurn objects.
"""

from __future__ import annotations

import re
from typing import Iterable

from discourse_engine.v4.models import Dialogue, DialogueTurn, SpeakerProfile, DialogueReport
from discourse_engine.v4.contradiction import DialogueContradictionAnalyzer
from discourse_engine.v4.evasion import DialogueEvasionAnalyzer
from discourse_engine.v4.power_dynamics import PowerDynamicsAnalyzer


# Specialized splitter for common interview-style transcripts.
_QA_SPLIT_RE = re.compile(r"(Interviewer|Politician):\s*")


def _normalize_speaker_id(label: str) -> str:
    """Create a stable, lowercase speaker id from a display label."""
    base = label.strip().lower()
    base = re.sub(r"\s+", "_", base)
    base = re.sub(r"[^a-z0-9_]+", "", base)
    return base or "speaker"


def parse_speaker_tagged_text(text: str) -> Dialogue:
    """
    Parse a simple transcript format into a Dialogue.

    Primary path (interview-style):
    - Uses explicit labels like `Interviewer:` and `Politician:` anywhere in the text.

    Fallback path:
    - Treats each line starting with `Speaker:` as a new turn.
    """
    text = text.strip()
    turns: list[DialogueTurn] = []
    profiles: dict[str, SpeakerProfile] = {}

    # --- Primary: interview-style splitter (handles multiple speakers on one long line) ---
    if "Interviewer:" in text or "Politician:" in text:
        parts = _QA_SPLIT_RE.split(text)
        # parts = ["", "Interviewer", "text...", "Politician", "text...", ...]
        # Skip any leading preamble before the first label.
        for i in range(1, len(parts), 2):
            label = parts[i].strip()
            if i + 1 >= len(parts):
                continue
            content = parts[i + 1].strip()
            if not content:
                continue

            speaker_id = _normalize_speaker_id(label)
            profile = profiles.get(speaker_id)
            if profile is None:
                profile = SpeakerProfile(speaker_id=speaker_id, display_name=label)
                profiles[speaker_id] = profile

            turn_index = len(turns)
            turns.append(
                DialogueTurn(
                    speaker_id=speaker_id,
                    text=content,
                    turn_index=turn_index,
                    display_name=label,
                    role=profile.role,
                )
            )

        return Dialogue(turns=turns, speaker_profiles=profiles)

    # --- Fallback: generic "Speaker: text" per line ---
    lines = text.splitlines()
    current_turn: DialogueTurn | None = None

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue

        if ":" in line:
            label_part, content_part = line.split(":", 1)
            label = label_part.strip()
            content = content_part.strip()
            if label and content:
                speaker_id = _normalize_speaker_id(label)
                profile = profiles.get(speaker_id)
                if profile is None:
                    profile = SpeakerProfile(speaker_id=speaker_id, display_name=label)
                    profiles[speaker_id] = profile

                turn_index = len(turns)
                current_turn = DialogueTurn(
                    speaker_id=speaker_id,
                    text=content,
                    turn_index=turn_index,
                    display_name=label,
                    role=profile.role,
                )
                turns.append(current_turn)
                continue

        # Continuation of the previous speaker's turn, or anonymous if none yet.
        if current_turn is None:
            anon_id = "speaker"
            if anon_id not in profiles:
                profiles[anon_id] = SpeakerProfile(speaker_id=anon_id, display_name=None)
            current_turn = DialogueTurn(
                speaker_id=anon_id,
                text=line.strip(),
                turn_index=0,
                display_name=None,
            )
            turns.append(current_turn)
        else:
            if current_turn.text:
                current_turn.text += "\n" + line.strip()
            else:
                current_turn.text = line.strip()

    # Normalize turn indices in case we created an anonymous first turn midstream.
    for idx, t in enumerate(turns):
        t.turn_index = idx

    return Dialogue(turns=turns, speaker_profiles=profiles)


def dialogue_from_turns(turns: Iterable[DialogueTurn]) -> Dialogue:
    """Build a Dialogue and inferred SpeakerProfiles from existing turns."""
    turns_list = list(turns)
    profiles: dict[str, SpeakerProfile] = {}
    for t in turns_list:
        if t.speaker_id not in profiles:
            profiles[t.speaker_id] = SpeakerProfile(
                speaker_id=t.speaker_id,
                display_name=t.display_name,
                role=t.role,
            )
    # Ensure turn indices are sequential
    for idx, t in enumerate(turns_list):
        t.turn_index = idx
    return Dialogue(turns=turns_list, speaker_profiles=profiles)


def run_dialogue_analysis(turns: Iterable[DialogueTurn]) -> DialogueReport:
    """
    High-level v4 entrypoint for dialogue analysis.

    Accepts an iterable of DialogueTurn objects and returns a DialogueReport
    with contradiction, evasion, and power-dynamics subreports attached.
    """
    dialogue = dialogue_from_turns(turns)
    contradiction = DialogueContradictionAnalyzer().analyze(dialogue)
    evasion = DialogueEvasionAnalyzer().analyze(dialogue)
    power = PowerDynamicsAnalyzer().analyze(dialogue)
    return DialogueReport(
        dialogue=dialogue,
        contradictions=contradiction,
        evasion=evasion,
        power_dynamics=power,
    )


def run_dialogue_from_text(text: str) -> DialogueReport:
    """Convenience wrapper: parse speaker-tagged text and run full analysis."""
    dialogue = parse_speaker_tagged_text(text)
    return run_dialogue_analysis(dialogue.turns)


def dialogue_report_to_dict(report: DialogueReport) -> dict:
    """Convert a DialogueReport into a JSON-serializable dict."""
    dialogue = report.dialogue
    speakers = {
        speaker_id: {
            "display_name": profile.display_name,
            "role": profile.role,
        }
        for speaker_id, profile in dialogue.speaker_profiles.items()
    }

    turns = [
        {
            "turn_index": t.turn_index,
            "speaker_id": t.speaker_id,
            "display_name": t.display_name,
            "role": t.role,
            "text": t.text,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "acoustic_features": t.acoustic_features,
        }
        for t in dialogue.turns
    ]

    contradictions = None
    if report.contradictions is not None:
        contradictions = [
            {
                "speaker_a": c.speaker_a,
                "speaker_b": c.speaker_b,
                "contradictions": c.contradictions,
                "strongest_score": c.strongest_score,
            }
            for c in report.contradictions.cells
        ]

    evasion = None
    if report.evasion is not None:
        evasion = {
            "aggregate_score": report.evasion.aggregate_score,
            "summary": report.evasion.summary,
            "scores": [
                {
                    "turn_index": s.turn_index,
                    "question_index": s.question_index,
                    "score": s.score,
                    "reason": s.reason,
                }
                for s in report.evasion.scores
            ],
        }

    power = None
    if report.power_dynamics is not None:
        power = {
            "summary": report.power_dynamics.summary,
            "speakers": [
                {
                    "speaker_id": m.speaker_id,
                    "total_turns": m.total_turns,
                    "total_tokens": m.total_tokens,
                    "interruption_count": m.interruption_count,
                    "authority_score": m.authority_score,
                    "dominance_score": m.dominance_score,
                }
                for m in report.power_dynamics.speakers
            ],
        }

    return {
        "dialogue": {
            "speakers": speakers,
            "turns": turns,
        },
        "contradictions": {
            "cells": contradictions,
            "summary": report.contradictions.summary if report.contradictions else "",
        }
        if contradictions is not None
        else None,
        "evasion": evasion,
        "power_dynamics": power,
    }


def format_dialogue_report(report: DialogueReport) -> str:
    """Create a human-readable summary for CLI output."""
    lines: list[str] = []
    dialogue = report.dialogue
    speakers = list(dialogue.speaker_profiles.keys())
    lines.append("--- V4 Dialogue Analysis ---")
    lines.append(f"Turns: {len(dialogue.turns)}  Speakers: {', '.join(speakers) if speakers else '(none)'}")
    lines.append("")

    if report.contradictions:
        lines.append("Contradiction Matrix:")
        if report.contradictions.cells:
            for cell in report.contradictions.cells:
                lines.append(
                    f"- {cell.speaker_a} vs {cell.speaker_b}: "
                    f"{cell.contradictions} potential contradiction(s), "
                    f"max score={cell.strongest_score:.2f}"
                )
        else:
            lines.append("- (none)")
        lines.append("")

    if report.evasion:
        lines.append("Evasion Scorer:")
        lines.append(f"- Aggregate evasion score: {report.evasion.aggregate_score:.2f}")
        if report.evasion.scores:
            top = sorted(report.evasion.scores, key=lambda s: s.score, reverse=True)[:3]
            for s in top:
                lines.append(
                    f"  Turn {s.turn_index} (answer to question {s.question_index}): score={s.score:.2f} - {s.reason}"
                )
        else:
            lines.append("- (no evasive answers detected)")
        lines.append("")

    if report.power_dynamics:
        lines.append("Power Dynamics:")
        for m in report.power_dynamics.speakers:
            lines.append(
                f"- {m.speaker_id}: dominance={m.dominance_score:.2f}, "
                f"authority={m.authority_score:.2f}, "
                f"turns={m.total_turns}, interruptions={m.interruption_count}"
            )

    return "\n".join(lines)

