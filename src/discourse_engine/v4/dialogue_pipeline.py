"""v4 dialogue pipeline and text-format parsing utilities.

This module provides:
- Minimal data ingestion helpers for speaker-tagged transcripts.
- A future hook (`run_dialogue_analysis`) for full v4 analysis over DialogueTurn objects.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from discourse_engine.v4.models import (
    Dialogue,
    DialogueTurn,
    SpeakerProfile,
    DialogueReport,
)
from discourse_engine.v4.contradiction import DialogueContradictionAnalyzer
from discourse_engine.v4.evasion import DialogueEvasionAnalyzer
from discourse_engine.v4.power_dynamics import PowerDynamicsAnalyzer
from discourse_engine.v4.topic_tracker import TopicTracker
from discourse_engine.analyzers.logical_fallacy import LogicalFallacyAnalyzer


# Specialized splitter for common interview-style transcripts.
_QA_SPLIT_RE = re.compile(r"(Interviewer|Politician):\s*")

# Multi-speaker: any "Name: " where Name is one or more capitalized words.
_MULTISPEAKER_LABEL_RE = re.compile(
    r"([A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*)*):\s*"
)

# Gutenberg / source-tag scrubbers: common noise that prevents speaker detection.
_LEADING_SOURCE_TAG_RE = re.compile(
    r"^(?:\s*(?:`{1,3}|''|“”|\"\"|\[\d+\]|\(\d+\)|\d+\||\d{1,6}\s+))+\s*",
    re.MULTILINE,
)

# Prose dialogue patterns:
# - "Quote," said Holmes.
# - Holmes said, "Quote."
# - 'Quote,' said Mr. Watson.
_QUOTE_CHARS = "\"“”'‘’"
_QUOTE_SPAN_RE = re.compile(r"([\"“”'‘’])(.+?)\1", re.DOTALL)
_SAID_VERBS = (
    "said|asked|replied|cried|returned|murmured|whispered|shouted|exclaimed|answered|remarked|added|observed"
)
_TITLE = r"(?:Mr\.|Mrs\.|Ms\.|Miss|Dr\.|Inspector|Detective|Sir|Lady)"
_NAME = r"(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
_ATTR_AFTER_RE = re.compile(
    rf"(?:,\s*)?(?:{_SAID_VERBS})\s+(?:{_TITLE}\s+)?(?P<name>{_NAME}|he|she|they)\b",
)
_ATTR_BEFORE_RE = re.compile(
    rf"(?P<name>{_NAME}|{_TITLE}\s+{_NAME}|he|she|they)\s+(?:{_SAID_VERBS})\s*(?:,|:)?\s*$",
)


def _scrub_source_tags(text: str) -> str:
    """Remove leading numeric/source tag noise that blocks label regexes."""
    if not text:
        return text
    # Remove repeated leading tags per line/paragraph.
    return _LEADING_SOURCE_TAG_RE.sub("", text)


def _speaker_label_from_prose(name: str, last_named: str | None) -> str:
    n = (name or "").strip()
    if not n:
        return last_named or "Speaker_A"
    lowered = n.lower()
    if lowered in {"he", "she", "they"}:
        return last_named or ("Speaker_A" if lowered == "he" else "Speaker_B")
    return n


def _parse_prose_dialogue(text: str) -> Optional[Dialogue]:
    """Heuristic prose-to-tag converter for novels/literary dialogue.

    Extracts quoted spans and tries to attribute them to speakers based on nearby
    'said/asked/replied' patterns. Falls back to alternating speakers when needed.
    """
    raw = text.strip()
    if not raw:
        return None

    turns_list: list[DialogueTurn] = []
    profiles: dict[str, SpeakerProfile] = {}
    last_named: str | None = None
    alt_toggle = 0

    # Iterate quoted spans in order and assign speakers.
    for m in _QUOTE_SPAN_RE.finditer(raw):
        quote_text = (m.group(2) or "").strip()
        if not quote_text:
            continue

        after = raw[m.end() : m.end() + 120]
        before = raw[max(0, m.start() - 120) : m.start()]

        speaker_label: str | None = None

        m_after = _ATTR_AFTER_RE.search(after)
        if m_after:
            speaker_label = m_after.group("name")
        else:
            # Look for "Holmes said," immediately before the quote.
            tail = before.splitlines()[-1] if before else before
            m_before = _ATTR_BEFORE_RE.search(tail)
            if m_before:
                speaker_label = m_before.group("name")

        if speaker_label is None:
            speaker_label = "Speaker_A" if (alt_toggle % 2 == 0) else "Speaker_B"
            alt_toggle += 1

        speaker_label = _speaker_label_from_prose(speaker_label, last_named)
        if speaker_label not in {"Speaker_A", "Speaker_B"} and speaker_label.lower() not in {"he", "she", "they"}:
            last_named = speaker_label

        speaker_id = _normalize_speaker_id(speaker_label)
        if speaker_id not in profiles:
            profiles[speaker_id] = SpeakerProfile(
                speaker_id=speaker_id, display_name=speaker_label
            )

        turn_index = len(turns_list)
        turns_list.append(
            DialogueTurn(
                speaker_id=speaker_id,
                text=quote_text,
                turn_index=turn_index,
                display_name=speaker_label,
                role=profiles[speaker_id].role,
            )
        )

    if len(turns_list) < 2:
        return None

    return Dialogue(turns=turns_list, speaker_profiles=profiles)


def _normalize_speaker_id(label: str) -> str:
    """Create a stable, lowercase speaker id from a display label."""
    base = label.strip().lower()
    base = re.sub(r"\s+", "_", base)
    base = re.sub(r"[^a-z0-9_]+", "", base)
    return base or "speaker"


_NON_SPEAKER_LABEL_WORDS = {
    "chapter",
    "book",
    "part",
    "scene",
    "page",
    "contents",
    "preface",
    "appendix",
    "footnote",
    "illustration",
    "note",
    "printed",
}
_NON_NAME_CONNECTORS = {
    # These often appear in headings/narration, not human labels.
    "in",
    "of",
    "and",
    "to",
    "for",
    "from",
    "with",
    "on",
    "at",
    "by",
    "upon",
    "into",
    "over",
    "under",
    "through",
}


def _is_plausible_speaker_label(label: str) -> bool:
    """Heuristic filter to avoid treating prose headings as speakers."""
    l = (label or "").strip()
    if not l:
        return False
    words = [w for w in re.split(r"\s+", l) if w]
    if len(words) == 0 or len(words) > 3:
        return False

    # Reject common section/metadata headings.
    if any(w.lower().strip(".") in _NON_SPEAKER_LABEL_WORDS for w in words):
        return False

    # Reject connector-heavy headings like "Printed In Rather ..."
    # Allow "The X" as a role label (common in transcripts), but reject other
    # connectors beyond the first word.
    for idx, w in enumerate(words):
        lw = w.lower().strip(".")
        if idx == 0 and lw == "the":
            continue
        if idx > 0 and lw in _NON_NAME_CONNECTORS:
            return False

    return True


def _parse_multispeaker_inline(text: str) -> Optional[Dialogue]:
    """
    Split text by any "Name: " pattern (Name = capitalized word(s)) so that
    single-line input like "Manager A: ... CEO: ... Manager B: ..." yields
    multiple turns. Returns None if fewer than two speaker tags found.
    """
    text = text.strip()
    if not text:
        return None

    matches: list[tuple[int, int, str]] = []  # (start, end, label)
    for m in _MULTISPEAKER_LABEL_RE.finditer(text):
        preceding = text[: m.start()].rstrip()
        if not preceding or preceding[-1] in ".\n!?":
            label = m.group(1).strip()
            if label and _is_plausible_speaker_label(label):
                matches.append((m.start(), m.end(), label))

    if len(matches) < 2:
        return None

    turns_list: list[DialogueTurn] = []
    profiles: dict[str, SpeakerProfile] = {}

    for i, (_start, end, label) in enumerate(matches):
        content_start = end
        content_end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        content = text[content_start:content_end].strip()
        if not content:
            continue

        speaker_id = _normalize_speaker_id(label)
        if speaker_id not in profiles:
            profiles[speaker_id] = SpeakerProfile(speaker_id=speaker_id, display_name=label)

        turn_index = len(turns_list)
        turns_list.append(
            DialogueTurn(
                speaker_id=speaker_id,
                text=content,
                turn_index=turn_index,
                display_name=label,
                role=profiles[speaker_id].role,
            )
        )

    if not turns_list:
        return None

    return Dialogue(turns=turns_list, speaker_profiles=profiles)


def parse_speaker_tagged_text(text: str) -> Dialogue:
    """
    Parse a simple transcript format into a Dialogue.

    First: multi-speaker inline (any "Name: " in text, works without newlines).
    Then: interview-style (Interviewer/Politician).
    Fallback: line-by-line "Label: content".
    """
    text = _scrub_source_tags(text.strip())
    turns: list[DialogueTurn] = []
    profiles: dict[str, SpeakerProfile] = {}

    # --- First: multi-speaker normalizer (CEO:, Manager A:, Minister Vance:, etc.) ---
    multispeaker = _parse_multispeaker_inline(text)
    if multispeaker is not None and len(multispeaker.turns) >= 2:
        return multispeaker

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
            if label and content and _is_plausible_speaker_label(label):
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

    # If we failed to identify multiple speakers (or likely misidentified headings),
    # try prose dialogue heuristics. This enables novels / literary dialogue to still
    # yield a multi-speaker graph.
    plausible_profiles = [
        p for p in profiles.values() if p.display_name and _is_plausible_speaker_label(p.display_name)
    ]
    if len(turns) < 2 or len(plausible_profiles) < 2:
        prose = _parse_prose_dialogue(text)
        if prose is not None and len(prose.turns) >= 2:
            return prose

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
    topics = TopicTracker().analyze(dialogue)
    report = DialogueReport(
        dialogue=dialogue,
        contradictions=contradiction,
        evasion=evasion,
        power_dynamics=power,
    )
    # Attach topics via metadata (to avoid changing constructor signature everywhere).
    report.topics = topics  # type: ignore[attr-defined]
    return report


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

    topics = None
    # topics field is attached dynamically in run_dialogue_analysis
    if hasattr(report, "topics") and getattr(report, "topics") is not None:
        t = getattr(report, "topics")
        topics = {
            "summary": t.summary,
            "entities": [
                {"entity": e.entity, "consecutive_evasions": e.consecutive_evasions}
                for e in t.entities
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
        "topics": topics,
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
        lines.append("")

    # Topic threading / unresolved entities
    if hasattr(report, "topics") and getattr(report, "topics") is not None:
        topics = getattr(report, "topics")
        lines.append("Topic Threading:")
        lines.append(f"- {topics.summary}")
        lines.append("")

    # Discourse Profile (tactical signature): per-speaker dominance, evasion, primary tactic + fallacy habit.
    lines.append("Discourse Profile:")
    evasion_by_speaker: dict[str, list[float]] = {}
    if report.evasion and report.evasion.scores:
        for s in report.evasion.scores:
            if s.turn_index < len(dialogue.turns):
                spk = dialogue.turns[s.turn_index].speaker_id
                evasion_by_speaker.setdefault(spk, []).append(s.score)

    # Compute fallacy habits per speaker by analyzing each turn's text.
    fallacy_counts: dict[str, dict[str, int]] = {}
    for t in dialogue.turns:
        if not t.text:
            continue
        for f in LogicalFallacyAnalyzer().analyze(t.text):
            ftype = f.fallacy_type or f.name
            bucket = fallacy_counts.setdefault(t.speaker_id, {})
            bucket[ftype] = bucket.get(ftype, 0) + 1

    for m in report.power_dynamics.speakers if report.power_dynamics else []:
        avg_evasion = 0.0
        if m.speaker_id in evasion_by_speaker and evasion_by_speaker[m.speaker_id]:
            avg_evasion = sum(evasion_by_speaker[m.speaker_id]) / len(
                evasion_by_speaker[m.speaker_id]
            )
        tactic = "Fact-based / Questioning"
        if m.dominance_score >= 0.5 and avg_evasion >= 0.5:
            tactic = "Evasion / Redefinition"
        elif m.dominance_score >= 0.5:
            tactic = "Dominant"
        elif avg_evasion >= 0.5:
            tactic = "Evasion"

        habit = "None detected"
        counts = fallacy_counts.get(m.speaker_id) or {}
        if counts:
            habit_type = max(counts.items(), key=lambda kv: kv[1])[0]
            habit = habit_type.replace("_", " ")

        lines.append(
            f"- {m.speaker_id}: dominance={m.dominance_score:.2f}, "
            f"evasion={avg_evasion:.2f}, tactic={tactic}, fallacy_habit={habit}"
        )

    return "\n".join(lines)

