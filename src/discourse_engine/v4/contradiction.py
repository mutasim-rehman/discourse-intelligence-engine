"""Dialogue-level contradiction matrix over turns.

Wraps the v3 ContradictionAnalyzer and summarizes results per speaker pair.
"""

from __future__ import annotations

from collections import defaultdict

from discourse_engine.v4.models import (
    ContradictionCell,
    ContradictionMatrix,
    Dialogue,
)


class DialogueContradictionAnalyzer:
    """Builds a contradiction matrix from a Dialogue."""

    def __init__(self, min_overlap: float = 0.15) -> None:
        self.min_overlap = min_overlap

    def analyze(self, dialogue: Dialogue) -> ContradictionMatrix:
        """Analyze a Dialogue and return an aggregated contradiction matrix."""
        try:
            # Reuse existing heuristic contradiction logic from v3.
            from discourse_engine.v3.contradiction import ContradictionAnalyzer
        except Exception as exc:  # pragma: no cover - defensive
            return ContradictionMatrix(
                cells=[],
                summary=f"Contradiction analysis unavailable: {exc}",
            )

        turns_seq = [(t.speaker_id, t.text) for t in dialogue.turns]
        report = ContradictionAnalyzer().analyze(turns_seq, min_overlap=self.min_overlap)

        agg: dict[tuple[str, str], ContradictionCell] = {}
        for pair in report.pairs:
            key = (pair.speaker_a, pair.speaker_b)
            cell = agg.get(key)
            if cell is None:
                cell = ContradictionCell(
                    speaker_a=pair.speaker_a,
                    speaker_b=pair.speaker_b,
                    contradictions=0,
                    strongest_score=0.0,
                )
                agg[key] = cell
            cell.contradictions += 1
            cell.strongest_score = max(cell.strongest_score, pair.probability)

        cells = list(agg.values())
        if not cells:
            summary = f"Analyzed {len(dialogue.turns)} turns. No strong contradictions detected."
        else:
            unique_speakers = {t.speaker_id for t in dialogue.turns}
            summary = (
                f"Analyzed {len(dialogue.turns)} turns from {len(unique_speakers)} speaker(s). "
                f"{len(cells)} speaker pair(s) show potential contradictions."
            )

        return ContradictionMatrix(cells=cells, summary=summary)

