"""Debate Heatmap & Influence Visualization.

Computes per-turn metrics for emotional intensity, dominance, and certainty.
Produces heatmap grid data for visualization.
"""

import re

from discourse_engine.v3.models import DebateHeatmapReport, TurnMetrics


INTENSITY_TERMS = {
    "must", "need", "urgent", "critical", "crisis", "protect", "defend",
    "threat", "attack", "fear", "danger", "never", "always", "certain",
    "absolute", "everyone", "destroy", "collapse",
}
DOMINANCE_TERMS = {"must", "shall", "will", "cannot", "never", "always", "everyone"}
CERTAINTY_MODALS = {"must", "will", "shall", "cannot"}


def _intensity_score(text: str) -> float:
    lower = text.lower()
    words = re.findall(r"\b\w+\b", lower)
    if not words:
        return 0.0
    count = sum(1 for w in words if w in INTENSITY_TERMS)
    return min(count / len(words) * 10, 1.0)


def _dominance_score(text: str) -> float:
    lower = text.lower()
    words = lower.split()
    if not words:
        return 0.0
    count = sum(1 for w in words if re.sub(r"\W", "", w) in DOMINANCE_TERMS)
    return min(count / len(words) * 5, 1.0)


def _certainty_score(text: str) -> float:
    lower = text.lower()
    words = lower.split()
    if not words:
        return 0.0
    count = sum(1 for w in words if re.sub(r"\W", "", w) in CERTAINTY_MODALS)
    return min(count / len(words) * 8, 1.0)


class DebateHeatmapAnalyzer:
    """
    Produces heatmap and influence metrics from speaker turns.
    """

    def __init__(self, time_bins: int = 10) -> None:
        """
        Args:
            time_bins: Number of time bins for heatmap grid (columns).
        """
        self.time_bins = time_bins

    def analyze(
        self,
        turns: list[tuple[str, str]],
    ) -> DebateHeatmapReport:
        """
        Analyze speaker turns for heatmap visualization.

        Args:
            turns: [(speaker_id, text), ...]
        """
        speakers = list(dict.fromkeys(s[0] for s in turns))
        speaker_to_idx = {s: i for i, s in enumerate(speakers)}

        turn_metrics: list[TurnMetrics] = []
        for idx, (speaker_id, text) in enumerate(turns):
            turn_metrics.append(
                TurnMetrics(
                    speaker_id=speaker_id,
                    turn_idx=idx,
                    text=text[:100] + ("..." if len(text) > 100 else ""),
                    emotional_intensity=_intensity_score(text),
                    dominance_score=_dominance_score(text),
                    certainty_score=_certainty_score(text),
                    word_count=len(text.split()),
                )
            )

        # Heatmap grid: rows=speakers, cols=time_bins
        bin_size = max(1, len(turns) // self.time_bins)
        heatmap = [[0.0] * self.time_bins for _ in speakers]
        for bin_idx in range(self.time_bins):
            start = bin_idx * bin_size
            end = min(start + bin_size, len(turns))
            for t_idx in range(start, end):
                t = turn_metrics[t_idx]
                s_idx = speaker_to_idx[t.speaker_id]
                intensity = t.emotional_intensity + t.dominance_score * 0.5
                heatmap[s_idx][bin_idx] = max(
                    heatmap[s_idx][bin_idx],
                    intensity,
                )

        escalation = [t.emotional_intensity + t.dominance_score for t in turn_metrics]

        influence_scores: dict[str, float] = {}
        for s in speakers:
            s_turns = [tm for tm in turn_metrics if tm.speaker_id == s]
            if s_turns:
                influence_scores[s] = sum(
                    tm.emotional_intensity + tm.dominance_score
                    for tm in s_turns
                ) / len(s_turns)
            else:
                influence_scores[s] = 0.0

        summary = (
            f"Analyzed {len(turns)} turns from {len(speakers)} speaker(s). "
            f"Influence: {', '.join(f'{s}={influence_scores[s]:.2f}' for s in speakers)}."
        )

        viz_data = {
            "heatmap": heatmap,
            "speakers": speakers,
            "time_bins": self.time_bins,
            "escalation": escalation,
            "influence": influence_scores,
        }

        return DebateHeatmapReport(
            turns=turn_metrics,
            speakers=speakers,
            heatmap_grid=heatmap,
            escalation_by_turn=escalation,
            influence_scores=influence_scores,
            summary=summary,
            viz_data=viz_data,
        )
