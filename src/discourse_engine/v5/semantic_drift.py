"""Semantic drift detector for V5.

Compares the first 10% and last 10% of a document to detect
shifts like "voluntary" → "mandatory" over time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


VOLUNTARY_TERMS = [
    "voluntary",
    "optional",
    "up to you",
    "if you want",
    "no obligation",
]

MANDATORY_TERMS = [
    "mandatory",
    "required",
    "obligatory",
    "must",
    "compulsory",
    "mandatory rollout",
]


def _count_terms(text: str, terms: List[str]) -> int:
    lower = text.lower()
    return sum(lower.count(t) for t in terms)


@dataclass
class DriftSignal:
    name: str
    first_count: int
    last_count: int
    summary: str


def compute_semantic_drift(text: str) -> Dict[str, object]:
    """Return a lightweight semantic drift summary between early and late segments.

    Currently focuses on "voluntary" → "mandatory" style shifts.
    """
    text = text or ""
    n = len(text)
    if n < 200:
        return {}

    span = max(int(n * 0.1), 100)
    first = text[:span]
    last = text[-span:]

    voluntary_first = _count_terms(first, VOLUNTARY_TERMS)
    voluntary_last = _count_terms(last, VOLUNTARY_TERMS)
    mandatory_first = _count_terms(first, MANDATORY_TERMS)
    mandatory_last = _count_terms(last, MANDATORY_TERMS)

    signals: List[DriftSignal] = []

    if voluntary_first > 0 and mandatory_last > mandatory_first:
        signals.append(
            DriftSignal(
                name="voluntary_to_mandatory",
                first_count=voluntary_first,
                last_count=mandatory_last,
                summary=(
                    "Project described with voluntary framing early in the document, "
                    "but more mandatory/required language appears toward the end."
                ),
            )
        )

    if not signals:
        return {}

    return {
        "signals": [
            {
                "name": s.name,
                "first_count": s.first_count,
                "last_count": s.last_count,
                "summary": s.summary,
            }
            for s in signals
        ],
        "first_span_chars": span,
        "last_span_chars": span,
    }

