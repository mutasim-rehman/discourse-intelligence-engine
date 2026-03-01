"""Cross-Speaker Contradiction Detection.

Detects contradictions, reframing, and evasion between speakers in debates/interviews.
Uses heuristic methods (extensible to NLI models).
"""

import re

from discourse_engine.v3.models import ContradictionPair, ContradictionReport


NEGATIONS = {"not", "never", "no", "nobody", "nothing", "neither", "nor", "without"}
NEGATION_VERBS = {"deny", "reject", "refuse", "dispute", "contradict"}
HEDGING = {"perhaps", "maybe", "might", "could", "possibly", "sometimes", "allegedly"}
QUESTION_WORDS = {"what", "when", "where", "why", "how", "who", "which"}


def _has_negation(text: str) -> bool:
    lower = text.lower()
    words = set(re.findall(r"\b\w+\b", lower))
    return bool(words & NEGATIONS) or any(v in lower for v in NEGATION_VERBS)


def _semantic_overlap(text_a: str, text_b: str) -> float:
    words_a = set(re.findall(r"\b\w{3,}\b", text_a.lower()))
    words_b = set(re.findall(r"\b\w{3,}\b", text_b.lower()))
    if not words_a or not words_b:
        return 0.0
    overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
    return min(overlap, 1.0)


def _hedging_density(text: str) -> float:
    lower = text.lower()
    words = lower.split()
    if not words:
        return 0.0
    count = sum(1 for w in words if re.sub(r"\W", "", w) in HEDGING)
    return count / len(words)


def _is_question(text: str) -> bool:
    stripped = text.strip()
    if not stripped.endswith("?"):
        return False
    first = stripped.lower().split()[0] if stripped.split() else ""
    return first in QUESTION_WORDS or stripped.startswith("Do ") or stripped.startswith("Did ")


class ContradictionAnalyzer:
    """Detects contradictions and strategic patterns between speaker turns."""

    def analyze(
        self,
        turns: list[tuple[str, str]],
        min_overlap: float = 0.15,
    ) -> ContradictionReport:
        """
        Analyze speaker turns for contradictions.
        turns: [(speaker_id, text), ...]
        """
        pairs: list[ContradictionPair] = []
        evasion_count = 0
        question_count = 0

        for i in range(len(turns) - 1):
            speaker_a, text_a = turns[i]
            speaker_b, text_b = turns[i + 1]
            overlap = _semantic_overlap(text_a, text_b)
            neg_a, neg_b = _has_negation(text_a), _has_negation(text_b)

            if neg_a != neg_b and overlap >= min_overlap and len(text_a) > 20 and len(text_b) > 20:
                prob = min(0.5 + overlap * 0.5, 0.9)
                pairs.append(
                    ContradictionPair(
                        speaker_a=speaker_a,
                        text_a=text_a[:200] + ("..." if len(text_a) > 200 else ""),
                        speaker_b=speaker_b,
                        text_b=text_b[:200] + ("..." if len(text_b) > 200 else ""),
                        probability=prob,
                        contradiction_type="direct",
                        explanation="Negation in one utterance with semantic overlap in the other.",
                    )
                )

            if _is_question(text_a):
                question_count += 1
                if _hedging_density(text_b) > 0.1 and overlap < 0.3:
                    evasion_count += 1

        reframing_detected = len(pairs) > 0
        evasion_likelihood = evasion_count / (question_count + 1)
        question_avoidance = evasion_count >= 1 and question_count >= 1
        summary = f"Analyzed {len(turns)} turns. Detected {len(pairs)} potential contradiction(s)."
        if evasion_likelihood > 0.3:
            summary += " Question avoidance or deflection likely."

        return ContradictionReport(
            pairs=pairs,
            reframing_detected=reframing_detected,
            evasion_likelihood=evasion_likelihood,
            question_avoidance_detected=question_avoidance,
            summary=summary,
        )
