"""Dialogue-level contradiction matrix over turns.

Wraps the v3 ContradictionAnalyzer and summarizes results per speaker pair.
"""

from __future__ import annotations

from collections import defaultdict
import re

from discourse_engine.v4.models import (
    ContradictionCell,
    ContradictionMatrix,
    Dialogue,
)
from discourse_engine.v4.evasion import DialogueEvasionAnalyzer


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

        # If no direct contradictions were detected, fall back to contextual contradictions
        # based on high evasion and low semantic overlap between question/answer pairs.
        if not cells and len(dialogue.turns) >= 2:
            evasion = DialogueEvasionAnalyzer().analyze(dialogue)
            if evasion.aggregate_score >= 0.5 and evasion.scores:
                # Simple semantic-overlap heuristic for contextual clashes.
                def _semantic_overlap(a: str, b: str) -> float:
                    wa = set(re.findall(r"\b\w{3,}\b", (a or "").lower()))
                    wb = set(re.findall(r"\b\w{3,}\b", (b or "").lower()))
                    if not wa or not wb:
                        return 0.0
                    return len(wa & wb) / min(len(wa), len(wb))

                speakers = list(dict.fromkeys(t.speaker_id for t in dialogue.turns))
                if len(speakers) == 2:
                    a, b = speakers
                    ctx_score = evasion.aggregate_score
                    # Only treat as contextual contradiction if at least one high-evasion answer
                    # also has very low lexical overlap with its triggering question.
                    has_contextual = False
                    for s in evasion.scores:
                        if (
                            s.question_index is not None
                            and 0 <= s.question_index < len(dialogue.turns)
                            and 0 <= s.turn_index < len(dialogue.turns)
                        ):
                            q = dialogue.turns[s.question_index].text or ""
                            ans = dialogue.turns[s.turn_index].text or ""
                            if _semantic_overlap(q, ans) < 0.2 and s.score >= 0.5:
                                has_contextual = True
                                break

                    if has_contextual:
                        cells = [
                            ContradictionCell(
                                speaker_a=a,
                                speaker_b=b,
                                contradictions=1,
                                strongest_score=ctx_score,
                            ),
                            ContradictionCell(
                                speaker_a=b,
                                speaker_b=a,
                                contradictions=1,
                                strongest_score=ctx_score,
                            ),
                        ]

        if not cells:
            summary = f"Analyzed {len(dialogue.turns)} turns. No strong contradictions detected."
        else:
            unique_speakers = {t.speaker_id for t in dialogue.turns}
            summary = (
                f"Analyzed {len(dialogue.turns)} turns from {len(unique_speakers)} speaker(s). "
                f"{len(cells)} speaker pair(s) show potential contradictions."
            )

        return ContradictionMatrix(cells=cells, summary=summary)

