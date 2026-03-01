"""Narrative Arc & Power Dynamics Modeling.

Models rhetorical evolution across time within a single document:
- Threat escalation
- Emotional intensity curve
- Framing shifts (fear, authority, identity)
- Pronoun distribution (we/they polarization)
- Agency shifts
"""

import json
import re
from pathlib import Path

from discourse_engine.utils.text_utils import split_sentences
from discourse_engine.v3.models import ChunkMetrics, NarrativeArcReport


def _load_lexicon(lexicon_dir: Path, name: str) -> list[str]:
    path = lexicon_dir / f"{name}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _count_matches(text: str, terms: list[str]) -> int:
    lower = text.lower()
    return sum(1 for t in terms if t.lower() in lower)


def _count_to_normalized(count: int, word_count: int) -> float:
    """Map count to 0-1 scale (bounded by density)."""
    if word_count == 0:
        return 0.0
    density = count / word_count
    return min(density * 20, 1.0)  # ~0.05 per 100 words = 1.0


# Tone intensifiers for emotional intensity
INTENSITY_TERMS = {
    "must", "need", "urgent", "critical", "crisis", "protect", "defend",
    "threat", "attack", "fear", "danger", "collapse", "destroy", "never",
    "always", "everyone", "everybody", "certain", "absolute", "total",
}

# Passive voice pattern: be + past participle
PASSIVE_PATTERN = re.compile(
    r"\b(?:is|are|was|were|be|been|being)\s+[\w]+ed\b",
    re.IGNORECASE,
)


class NarrativeArcAnalyzer:
    """
    Analyzes narrative arc and power dynamics across document chunks.

    Produces time-series metrics for visualization and escalation detection.
    """

    def __init__(self, lexicon_dir: Path | None = None, chunk_size: int = 5) -> None:
        if lexicon_dir is None:
            lexicon_dir = Path(__file__).parent.parent / "lexicons"
        self.lexicon_dir = Path(lexicon_dir)
        self.chunk_size = chunk_size
        self._fear = _load_lexicon(self.lexicon_dir, "fear_terms")
        self._authority = _load_lexicon(self.lexicon_dir, "authority_terms")
        self._identity = _load_lexicon(self.lexicon_dir, "identity_terms")
        if not self._fear:
            self._fear = ["collapse", "destroy", "threat", "danger", "crisis"]

    def _chunk_text(self, text: str) -> list[tuple[int, int, str]]:
        """Return [(start_idx, end_idx, chunk_text), ...]."""
        sentences = split_sentences(text)
        chunks: list[tuple[int, int, str]] = []
        for i in range(0, len(sentences), self.chunk_size):
            end = min(i + self.chunk_size, len(sentences))
            chunk_sents = sentences[i:end]
            chunks.append((i, end, " ".join(chunk_sents)))
        if not chunks and text.strip():
            chunks.append((0, 1, text.strip()))
        return chunks

    def _analyze_chunk(
        self,
        chunk_idx: int,
        start: int,
        end: int,
        chunk_text: str,
        total_sentences: int,
    ) -> ChunkMetrics:
        words = chunk_text.split()
        word_count = len(words)
        sent_count = end - start
        lower = chunk_text.lower()

        # Emotional intensity
        intensity_count = sum(1 for w in re.findall(r"\b\w+\b", lower) if w in INTENSITY_TERMS)
        emotional_intensity = _count_to_normalized(intensity_count, word_count) if word_count else 0.0

        # Fear, authority, identity (0-1)
        fear_count = _count_matches(chunk_text, self._fear)
        authority_count = _count_matches(chunk_text, self._authority)
        identity_count = _count_matches(chunk_text, self._identity)
        fear_score = _count_to_normalized(fear_count, word_count) if word_count else 0.0
        authority_score = _count_to_normalized(authority_count, word_count) if word_count else 0.0
        identity_score = _count_to_normalized(identity_count, word_count) if word_count else 0.0

        # Pronoun we/they ratio
        we_us = sum(lower.split().count(w) for w in ("we", "us"))
        they_them = sum(lower.split().count(w) for w in ("they", "them"))
        total_pn = we_us + they_them
        pronoun_we_they_ratio = we_us / (they_them + 1) if they_them else (we_us if we_us else 0.5)

        # Modal density
        modals = {"must", "should", "could", "would", "might", "can", "will", "shall"}
        modal_count = sum(1 for w in words if re.sub(r"\W", "", w.lower()) in modals)
        modal_density = modal_count / word_count if word_count else 0.0

        # Threat score (fear terms)
        threat_score = fear_score

        # Agency: passive voice ratio
        passive_matches = len(PASSIVE_PATTERN.findall(chunk_text))
        agency_passive_ratio = passive_matches / (sent_count + 1)

        total_chunks = max(1, (total_sentences + self.chunk_size - 1) // self.chunk_size)
        position = (chunk_idx + 0.5) / total_chunks

        return ChunkMetrics(
            chunk_idx=chunk_idx,
            position=position,
            sentence_start=start,
            sentence_end=end,
            emotional_intensity=min(emotional_intensity, 1.0),
            fear_score=min(fear_score, 1.0),
            authority_score=min(authority_score, 1.0),
            identity_score=min(identity_score, 1.0),
            pronoun_we_they_ratio=min(pronoun_we_they_ratio, 5.0),
            modal_density=min(modal_density, 1.0),
            threat_score=min(threat_score, 1.0),
            agency_passive_ratio=min(agency_passive_ratio, 1.0),
        )

    def analyze(self, text: str) -> NarrativeArcReport:
        """Compute narrative arc metrics across document chunks."""
        if not text or not text.strip():
            return NarrativeArcReport(
                chunks=[],
                escalation_points=[],
                dominant_framing_shifts=[],
                summary="No text to analyze.",
                viz_data={},
            )

        chunks_data = self._chunk_text(text)
        total_sentences = len(split_sentences(text))
        metrics_list: list[ChunkMetrics] = []

        for idx, (start, end, chunk_text) in enumerate(chunks_data):
            m = self._analyze_chunk(idx, start, end, chunk_text, total_sentences)
            metrics_list.append(m)

        # Escalation: chunks where emotional_intensity or threat spikes
        intensities = [c.emotional_intensity + c.threat_score for c in metrics_list]
        avg = sum(intensities) / len(intensities) if intensities else 0
        escalation_points = [
            i for i, v in enumerate(intensities)
            if v > avg + 0.15 and v > 0.3
        ]

        # Dominant framing shifts: when primary dimension changes
        def dominant(m: ChunkMetrics) -> str:
            scores = [("fear", m.fear_score), ("authority", m.authority_score), ("identity", m.identity_score)]
            return max(scores, key=lambda x: x[1])[0] if scores else "neutral"

        shifts: list[tuple[int, str]] = []
        prev_dom = None
        for i, m in enumerate(metrics_list):
            d = dominant(m)
            if prev_dom is not None and d != prev_dom and (m.fear_score > 0.1 or m.authority_score > 0.1 or m.identity_score > 0.1):
                shifts.append((i, d))
            prev_dom = d

        summary_parts = [
            f"Analyzed {len(metrics_list)} chunks ({total_sentences} sentences).",
        ]
        if escalation_points:
            summary_parts.append(f"Escalation at chunks: {escalation_points}.")
        if shifts:
            summary_parts.append(f"Framing shifts: {len(shifts)} detected.")

        viz_data = {
            "x": [c.position for c in metrics_list],
            "emotional_intensity": [c.emotional_intensity for c in metrics_list],
            "fear": [c.fear_score for c in metrics_list],
            "authority": [c.authority_score for c in metrics_list],
            "identity": [c.identity_score for c in metrics_list],
            "threat": [c.threat_score for c in metrics_list],
            "escalation_points": escalation_points,
        }

        return NarrativeArcReport(
            chunks=metrics_list,
            escalation_points=escalation_points,
            dominant_framing_shifts=shifts,
            summary=" ".join(summary_parts),
            viz_data=viz_data,
        )
