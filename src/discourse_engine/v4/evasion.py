"""Dialogue-level evasion (question dodging) scorer."""

from __future__ import annotations

import re
from typing import Iterable

from discourse_engine.analyzers.logical_fallacy import LogicalFallacyAnalyzer
from discourse_engine.v4.models import Dialogue, DialogueTurn, EvasionScore, EvasionSummary


HEDGING = {"perhaps", "maybe", "might", "could", "possibly", "sometimes", "allegedly"}
QUESTION_WORDS = {"what", "when", "where", "why", "how", "who", "which"}
STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "then",
    "than",
    "that",
    "this",
    "these",
    "those",
    "for",
    "from",
    "with",
    "about",
    "into",
    "onto",
    "of",
    "on",
    "in",
    "at",
    "by",
    "to",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    "just",
    "only",
    "also",
    "even",
    "very",
    "really",
    "so",
    "such",
    "up",
    "out",
    "over",
    "under",
    "again",
    "more",
    "most",
    "some",
    "any",
    "all",
    "no",
    "not",
    "own",
    "same",
    "other",
    "another",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "me",
    "him",
    "her",
    "us",
    "them",
    "my",
    "your",
    "his",
    "its",
    "our",
    "their",
}


def _hedging_density(text: str) -> float:
    lower = text.lower()
    words = lower.split()
    if not words:
        return 0.0
    count = sum(1 for w in words if re.sub(r"\\W", "", w) in HEDGING)
    return count / len(words)


def _semantic_overlap(text_a: str, text_b: str) -> float:
    words_a = set(re.findall(r"\\b\\w{3,}\\b", text_a.lower()))
    words_b = set(re.findall(r"\\b\\w{3,}\\b", text_b.lower()))
    if not words_a or not words_b:
        return 0.0
    overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
    return min(overlap, 1.0)


def _content_words(text: str) -> set[str]:
    """Approximate noun/phrase anchors by stripping stopwords and short tokens."""
    lower = text.lower()
    tokens = re.findall(r"\b\w{3,}\b", lower)
    return {t for t in tokens if t not in STOPWORDS}


def _is_question(text: str) -> bool:
    stripped = text.strip()
    if not stripped.endswith("?"):
        return False
    tokens = stripped.split()
    if not tokens:
        return False
    # Look for a question word or auxiliary anywhere (handles vocatives and preambles).
    for tok in tokens:
        base = re.sub(r"\W", "", tok).lower()
        if base in QUESTION_WORDS:
            return True
        if base in {
            "do",
            "did",
            "is",
            "are",
            "can",
            "could",
            "will",
            "would",
            "should",
            "shall",
            "have",
            "has",
        }:
            return True
    return False


class DialogueEvasionAnalyzer:
    """Scores how directly answers address preceding questions."""

    def analyze(self, dialogue: Dialogue) -> EvasionSummary:
        scores: list[EvasionScore] = []
        turns = dialogue.turns

        for idx, turn in enumerate(turns[:-1]):
            if not _is_question(turn.text):
                continue

            # First non-question turn from a different speaker is considered the primary answer.
            answer_idx = None
            for j in range(idx + 1, len(turns)):
                if turns[j].speaker_id != turn.speaker_id:
                    answer_idx = j
                    break
            if answer_idx is None:
                continue

            question_text = turn.text
            answer_text = turns[answer_idx].text
            overlap = _semantic_overlap(question_text, answer_text)
            hedge = _hedging_density(answer_text)

            # Base evasion: low semantic overlap AND high hedging.
            base = 1.0 - overlap  # 1 when overlap is 0
            score = max(0.0, min(1.0, 0.6 * base + 0.4 * min(hedge * 2.0, 1.0)))

            # Noun/phrase (content word) overlap: if the core entities of the question
            # never appear in the answer, treat it as strongly evasive even when abstract
            # words (like "transparency") are mirrored.
            q_content = _content_words(question_text)
            a_content = _content_words(answer_text)
            if q_content:
                shared = q_content & a_content
                coverage = len(shared) / len(q_content)
                if coverage < 0.2:
                    score = max(score, 0.75)

            # If the answer itself contains a Red Herring fallacy, treat it as strongly evasive,
            # even when lexical overlap is high (keyword mirroring without addressing the premise).
            fallacies = LogicalFallacyAnalyzer().analyze(answer_text)
            if any(getattr(f, "fallacy_type", None) == "red_herring" for f in fallacies):
                score = max(score, 0.8)

            if score < 0.15:
                continue  # treat very low scores as non-evasive

            reason = f"Low overlap with question (overlap={overlap:.2f}), hedging={hedge:.2f}."
            scores.append(
                EvasionScore(
                    turn_index=answer_idx,
                    question_index=idx,
                    score=score,
                    reason=reason,
                )
            )

        if scores:
            aggregate = sum(s.score for s in scores) / len(scores)
            summary = (
                f"Detected {len(scores)} potentially evasive answer(s). "
                f"Aggregate evasion score: {aggregate:.2f}."
            )
        else:
            aggregate = 0.0
            summary = "No strong signs of question dodging detected."

        return EvasionSummary(scores=scores, aggregate_score=aggregate, summary=summary)

