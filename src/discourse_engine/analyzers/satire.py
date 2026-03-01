"""Heuristic satire and absurdity detection.

Detects text that may be satirical, hyperbolic, or parodic rather than
genuine persuasion. Uses the formula:

    Satire = (Hyperbole * Absurdity * Incongruity) / Context_Plausibility

Key insight: Real political/war rhetoric uses intense language too.
Satire requires SEMANTIC ABSURDITY (impossible outcomes) and/or
self-undermining incongruity - not just emotional intensity.
"""

import re
from dataclasses import dataclass


@dataclass
class SatireSignal:
    """A detected signal that text may be satirical."""

    name: str
    description: str
    score: float  # 0-1 contribution


# === ABSURDITY: Semantic impossibility / playful exaggeration ===
# These are IMPLAUSIBLE in real political context. "Ruled by cats" = absurd.
# "Military operations in Iran" = plausible.
ABSURD_OUTCOME_PHRASES = (
    r"\bruled by cats\b",
    r"\bzombie\w*\b",
    r"\bchaos ruled by\b",
    r"\buniverse will collapse\b",
    r"\bsociety will (?:turn into|become)\s+\w+\s+(?:ruled by|run by)",
    r"\b(melt|explode|implode)\s+into\s+(?:cats|zombies|bananas)\b",
    r"\bend of (?:the )?universe\b",
    r"\bdeath panel\b",
    r"\bliterally\s+(?:everything|the worst)\b",
)
ABSURD_NOUNS = frozenset({
    "cats", "dogs", "penguins", "zombies", "aliens", "unicorns",
    "clowns", "potatoes", "bananas", "robots",
})
INCONGRUITY_PATTERN = re.compile(
    r"\b(?:ruled by|run by|led by|controlled by|governed by)\s+(\w+)",
    re.IGNORECASE,
)

# Disproportionate causation ONLY when consequence is absurd
# "one small change -> universe collapse" or "chaos ruled by cats"
DISPROPORTIONATE_ABSURD = re.compile(
    r"\b(?:if|when)\s+(?:we\s+)?(?:allow|pass|do)\s+(?:one\s+)?(?:small|tiny|minor|single)\s+"
    r"(?:\w+\s+){0,3}(?:change|policy|thing)\b.*?"
    r"(?:universe\s+will\s+collapse|chaos\s+ruled\s+by|ruled\s+by\s+(?:cats|zombies))",
    re.IGNORECASE | re.DOTALL,
)

# Self-undermining (satire mocks its own premise)
CONTRADICTION_MARKERS = (
    r"\bbecause\s+it\s+completely\s+ignores\b",
    r"\bperfect\s+because\s+it\s+(?:ignores|rejects)\b",
    r"\bthe\s+best\s+plan\s+that\s+ignores\b",
)

# === CONTEXT PLAUSIBILITY: Real-world political/military discourse ===
# High density = plausible context = LOWER satire probability
GEOPOLITICAL_TERMS = frozenset({
    "iran", "russia", "china", "korea", "syria", "iraq", "afghanistan",
    "military", "troops", "forces", "combat", "operations", "missiles",
    "nuclear", "weapons", "terrorist", "proxies", "regime", "administration",
    "congress", "senate", "president", "commander", "homeland", "vessels",
    "international", "shipping", "naval", "attack", "strike",
})


def _absurdity_score(text: str) -> float:
    """0-1: Semantic absurdity. High only for impossible/playful outcomes."""
    lower = text.lower()
    score = 0.0

    # Explicit absurd phrases
    for pat in ABSURD_OUTCOME_PHRASES:
        if re.search(pat, lower):
            score = max(score, 0.85)
            break

    # "Ruled by X" where X is absurd
    for m in INCONGRUITY_PATTERN.finditer(text):
        if m.group(1).lower() in ABSURD_NOUNS:
            score = max(score, 0.9)
            break

    # Trivial cause -> absurd consequence
    if DISPROPORTIONATE_ABSURD.search(text):
        score = max(score, 0.8)

    return score


def _incongruity_score(text: str) -> float:
    """0-1: Self-undermining, internal contradiction."""
    lower = text.lower()
    if any(re.search(pat, lower) for pat in CONTRADICTION_MARKERS):
        return 0.8
    return 0.0


def _hyperbole_score(text: str) -> float:
    """0-1: Intensifiers, absolutism. Note: War speeches have this too - not sufficient alone."""
    lower = text.lower()
    score = 0.0
    if re.search(r"\b(?:never|always|all|everyone|everybody)\b", lower):
        score += 0.2
    catastrophe_matches = len(re.findall(r"\b(?:collapse|destroy|chaos|catastrophe|certain death)\b", lower))
    score += min(0.2 + catastrophe_matches * 0.1, 0.4)  # multiple catastrophe words = stronger
    if re.search(r"\b(?:thousands|millions)\s+(?:and\s+)?(?:thousands|millions)\b", lower):
        score += 0.15
    if re.search(r"\b(?:perfect|completely|totally)\b", lower):
        score += 0.15
    return min(max(score, 0.2), 0.7)


def _context_plausibility_score(text: str) -> float:
    """0-1: Higher = more plausible real-world political/military context."""
    lower = text.lower()
    words = set(re.findall(r"\b[a-z]{4,}\b", lower))
    overlap = len(words & GEOPOLITICAL_TERMS)
    if overlap >= 5:
        return 0.9
    if overlap >= 3:
        return 0.7
    if overlap >= 1:
        return 0.5
    return 0.2


class SatireAnalyzer:
    """
    Satire detector using: Satire = (H * A * I) / (0.5 + C)

    - H = Hyperbole (intensity)
    - A = Absurdity (semantic impossibility) — GATE: if low, score collapses
    - I = Incongruity (self-undermining)
    - C = Context plausibility (real political/military discourse)

    War speeches have high H but low A and high C → low satire.
    """

    def analyze(self, text: str) -> tuple[float, list[SatireSignal], str]:
        """
        Returns:
            (probability, signals, content_type_hint)
        """
        if not text or not text.strip():
            return 0.0, [], "Uncertain"

        H = _hyperbole_score(text)
        A = _absurdity_score(text)
        I = _incongruity_score(text)
        C = _context_plausibility_score(text)

        signals: list[SatireSignal] = []

        if A > 0:
            signals.append(
                SatireSignal("Absurdity", "Semantic impossibility or playful exaggeration", A)
            )
        if I > 0.5:
            signals.append(
                SatireSignal("Incongruity", "Self-undermining or internal contradiction", I)
            )
        if H > 0.3:
            signals.append(
                SatireSignal("Hyperbole", "Intensifiers, absolutism (also common in rhetoric)", H)
            )
        if C > 0.5:
            signals.append(
                SatireSignal(
                    "Context plausibility",
                    "Real-world political/military discourse — lowers satire likelihood",
                    C,
                )
            )

        # Formula: H * (A + 1.5*I) / (0.5 + C)
        # Satire can come from absurdity OR incongruity. High C (plausible context) dampens.
        raw = H * (A + 1.5 * I)
        divisor = 0.5 + C
        probability = min(raw / divisor, 0.95)

        # Gate: Without absurdity AND without incongruity, cap satire (avoids war-speech false pos)
        if A < 0.4 and I < 0.4:
            probability = min(probability, 0.25)

        if probability >= 0.5:
            content_type = "Possibly Satire / Hyperbole"
        elif probability >= 0.25:
            content_type = "Uncertain (some satire signals)"
        else:
            content_type = "Persuasive Rhetoric (low satire probability)"

        return probability, signals, content_type
