"""Topic threading and unresolved-entity tracking for dialogues."""

from __future__ import annotations

import re
from dataclasses import dataclass

from discourse_engine.v4.models import Dialogue, TopicEntity, TopicTrackerSummary


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
}


def _content_words(text: str) -> set[str]:
    """Approximate topical entities by stripping stopwords and short tokens."""
    lower = text.lower()
    tokens = re.findall(r"\b\w{3,}\b", lower)
    return {t for t in tokens if t not in STOPWORDS}


def _is_question(text: str) -> bool:
    stripped = text.strip()
    if not stripped.endswith("?"):
        return False
    # Simple heuristic: has a question mark and a wh-word or auxiliary somewhere.
    tokens = stripped.split()
    if not tokens:
        return False
    question_words = {"what", "when", "where", "why", "how", "who", "which"}
    auxiliaries = {
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
    }
    for tok in tokens:
        base = re.sub(r"\W", "", tok).lower()
        if base in question_words or base in auxiliaries:
            return True
    return False


class TopicTracker:
    """Tracks unresolved topical entities (e.g. '$500 million', 'Zurich ledger')."""

    def analyze(self, dialogue: Dialogue) -> TopicTrackerSummary:
        turns = dialogue.turns
        if not turns:
            return TopicTrackerSummary(entities=[], summary="No dialogue turns to analyze.")

        unresolved: dict[str, int] = {}

        for idx, turn in enumerate(turns[:-1]):
            if not _is_question(turn.text or ""):
                continue

            # Identify the next answer from a different speaker.
            answer_idx = None
            for j in range(idx + 1, len(turns)):
                if turns[j].speaker_id != turn.speaker_id:
                    answer_idx = j
                    break
            if answer_idx is None:
                continue

            question_text = turn.text or ""
            answer_text = turns[answer_idx].text or ""
            q_entities = _content_words(question_text)
            a_entities = _content_words(answer_text)

            if not q_entities:
                continue

            shared = q_entities & a_entities
            coverage = len(shared) / len(q_entities)

            if coverage < 0.2:
                # Treat each entity in the question as further evaded.
                for ent in q_entities:
                    unresolved[ent] = unresolved.get(ent, 0) + 1
            else:
                # Entities directly addressed: reset their counters.
                for ent in shared:
                    unresolved[ent] = 0

        entities: list[TopicEntity] = [
            TopicEntity(entity=e, consecutive_evasions=count)
            for e, count in unresolved.items()
            if count > 0
        ]

        if not entities:
            return TopicTrackerSummary(entities=[], summary="No unresolved entities detected.")

        # Construct a compact human-readable summary for the most evaded entities.
        top = sorted(entities, key=lambda x: x.consecutive_evasions, reverse=True)[:3]
        parts = [
            f"'{t.entity}' evaded for {t.consecutive_evasions} consecutive turn(s)"
            for t in top
        ]
        summary = "Unresolved entities: " + "; ".join(parts) + "."
        return TopicTrackerSummary(entities=entities, summary=summary)

