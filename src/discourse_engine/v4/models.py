"""Dialogue data models for v4 dialogue analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpeakerProfile:
    """Profile for a dialogue participant."""

    speaker_id: str
    display_name: str | None = None
    role: str | None = None  # e.g. "CorporateExecutive", "Journalist"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogueTurn:
    """Single spoken/written turn in a dialogue."""

    speaker_id: str
    text: str
    turn_index: int
    display_name: str | None = None
    role: str | None = None
    start_time: float | None = None  # seconds from start, if available
    end_time: float | None = None
    # Optional acoustic features from audio analysis (pitch, volume, speaking rate, etc.)
    acoustic_features: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Dialogue:
    """Container for a multi-turn conversation."""

    turns: list[DialogueTurn]
    speaker_profiles: dict[str, SpeakerProfile] = field(default_factory=dict)


@dataclass
class ContradictionCell:
    """Aggregated contradiction strength between two speakers."""

    speaker_a: str
    speaker_b: str
    contradictions: int
    strongest_score: float


@dataclass
class ContradictionMatrix:
    """Matrix-style summary of contradictions in a dialogue."""

    cells: list[ContradictionCell]
    summary: str


@dataclass
class EvasionScore:
    """Evasion score for a single answer turn."""

    turn_index: int
    question_index: int | None
    score: float  # 0-1, higher = more evasive
    reason: str


@dataclass
class EvasionSummary:
    """Summary of question-dodging / evasion across the dialogue."""

    scores: list[EvasionScore]
    aggregate_score: float
    summary: str


@dataclass
class SpeakerPowerMetrics:
    """Per-speaker dominance / authority metrics."""

    speaker_id: str
    total_turns: int
    total_tokens: int
    interruption_count: int
    authority_score: float
    dominance_score: float


@dataclass
class PowerDynamicsSummary:
    """Aggregate view of power dynamics in the dialogue."""

    speakers: list[SpeakerPowerMetrics]
    summary: str


@dataclass
class DialogueReport:
    """Top-level v4 dialogue analysis report."""

    dialogue: Dialogue
    contradictions: ContradictionMatrix | None = None
    evasion: EvasionSummary | None = None
    power_dynamics: PowerDynamicsSummary | None = None


@dataclass
class TopicEntity:
    """A tracked topical entity (e.g. 'Zurich', '$500 million') and its evasion streak."""

    entity: str
    consecutive_evasions: int


@dataclass
class TopicTrackerSummary:
    """Summary of unresolved topical entities across a dialogue."""

    entities: list[TopicEntity]
    summary: str

