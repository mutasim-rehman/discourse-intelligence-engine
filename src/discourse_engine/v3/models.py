"""Shared data structures for v3 modules."""

from dataclasses import dataclass, field
from typing import Any


# --- Narrative Arc ---

@dataclass
class ChunkMetrics:
    """Metrics for a single text chunk in narrative arc analysis."""

    chunk_idx: int
    position: float  # 0-1, normalized position in document
    sentence_start: int
    sentence_end: int
    emotional_intensity: float
    fear_score: float
    authority_score: float
    identity_score: float
    pronoun_we_they_ratio: float
    modal_density: float
    threat_score: float
    agency_passive_ratio: float  # passive voice proportion


@dataclass
class NarrativeArcReport:
    """Full narrative arc analysis output."""

    chunks: list[ChunkMetrics]
    escalation_points: list[int]  # chunk indices where intensity spikes
    dominant_framing_shifts: list[tuple[int, str]]  # (chunk_idx, framing_type)
    summary: str
    viz_data: dict[str, Any] = field(default_factory=dict)


# --- Contradiction ---

@dataclass
class ContradictionPair:
    """A detected contradiction between two speaker utterances."""

    speaker_a: str
    text_a: str
    speaker_b: str
    text_b: str
    probability: float
    contradiction_type: str  # "direct" | "reframing" | "evasion"
    explanation: str


@dataclass
class ContradictionReport:
    """Cross-speaker contradiction analysis output."""

    pairs: list[ContradictionPair]
    reframing_detected: bool
    evasion_likelihood: float
    question_avoidance_detected: bool
    summary: str


# --- Temporal Drift ---

@dataclass
class DocumentProfile:
    """Rhetorical profile of a single document (for drift tracking)."""

    doc_id: str
    date: str | None
    fear: float
    authority: float
    identity: float
    liberty: float
    word_count: int


@dataclass
class DriftVector:
    """Change in a dimension between two documents."""

    dimension: str
    from_value: float
    to_value: float
    delta: float
    pct_change: float


@dataclass
class TemporalDriftReport:
    """Temporal rhetoric drift analysis output."""

    profiles: list[DocumentProfile]
    drift_vectors: list[DriftVector]
    timeline_data: list[dict[str, Any]]
    summary: str
    viz_data: dict[str, Any] = field(default_factory=dict)


# --- Debate Heatmap ---

@dataclass
class TurnMetrics:
    """Metrics for a single speaker turn."""

    speaker_id: str
    turn_idx: int
    text: str
    emotional_intensity: float
    dominance_score: float
    certainty_score: float
    word_count: int


@dataclass
class DebateHeatmapReport:
    """Debate heatmap analysis output."""

    turns: list[TurnMetrics]
    speakers: list[str]
    heatmap_grid: list[list[float]]  # [speaker][time_bin]
    escalation_by_turn: list[float]
    influence_scores: dict[str, float]
    summary: str
    viz_data: dict[str, Any] = field(default_factory=dict)
