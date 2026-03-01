"""Heuristic satire and absurdity detection.

Detects text that may be satirical, hyperbolic, or parodic rather than
genuine persuasion. Uses signal-based heuristics (no LLM required).
"""

import re
from dataclasses import dataclass


@dataclass
class SatireSignal:
    """A detected signal that text may be satirical."""

    name: str
    description: str
    score: float  # 0-1 contribution to satire probability


# Phrases that signal absurd/impossible outcomes (playful, hyperbolic)
ABSURD_OUTCOME_PHRASES = (
    r"\bruled by cats\b",
    r"\bzombie\w*\b",
    r"\bchaos ruled by\b",
    r"\buniverse will collapse\b",
    r"\bworld will end\b",
    r"\bsociety will (?:turn into|become)\s+\w+\s+(?:ruled by|run by)",
    r"\b(melt|explode|implode)\s+into\s+\w+",
    r"\bend of (?:the )?universe\b",
    r"\bliterally\s+(?:everything|the worst)\b",
    r"\b(\d+)\s+percent\s+(\w+\s+){0,2}(?:certified|guaranteed)\b",
    r"\bdeath panel\b",  # Known satirical political meme
)

# Disproportionate causation: trivial cause -> catastrophic effect
# "if [minor] then [extreme]" or "one small X will cause Y"
DISPROPORTIONATE_PATTERNS = (
    re.compile(
        r"\b(?:if|when)\s+(?:we\s+)?(?:allow|pass|do)\s+(?:one\s+)?(?:small|tiny|minor|single)\s+"
        r"(?:\w+\s+){0,3}(?:change|policy|thing)\b.*\b(?:will\s+)?(?:collapse|end|destroy|chaos|ruin)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:one|a single)\s+(?:\w+\s+){0,2}(?:change|mistake|error)\b.*\b(?:universe|world|society|civilization)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)

# Hyperbole + trivial trigger combo (small thing -> huge consequence)
TRIVIAL_TO_CATASTROPHE = re.compile(
    r"\b(?:small|tiny|minor|one|single|little)\b.*\b(?:collapse|chaos|destroy|end|ruin|catastrophe|apocalypse)\b",
    re.IGNORECASE | re.DOTALL,
)

# Semantic incongruity: serious framing + absurd noun
ABSURD_NOUNS = frozenset({
    "cats", "dogs", "penguins", "zombies", "aliens", "unicorns",
    "clowns", "potatoes", "bananas", "robots", "sentient",
})
INCONGRUITY_PATTERN = re.compile(
    r"\b(?:ruled by|run by|led by|controlled by|governed by)\s+(\w+)",
    re.IGNORECASE,
)

# Intentional self-undermining (satire often mocks its own premise)
CONTRADICTION_MARKERS = (
    r"\bbecause\s+it\s+completely\s+ignores\b",
    r"\bperfect\s+because\s+it\s+(?:ignores|rejects)\b",
    r"\bthe\s+best\s+plan\s+that\s+ignores\b",
)


def _count_absurd_outcomes(text: str) -> int:
    """Count matches of absurd outcome phrases."""
    lower = text.lower()
    count = 0
    for pat in ABSURD_OUTCOME_PHRASES:
        if re.search(pat, lower, re.IGNORECASE):
            count += 1
    return count


def _check_disproportionate_causation(text: str) -> bool:
    """True if text has trivial cause -> catastrophic effect structure."""
    for pat in DISPROPORTIONATE_PATTERNS:
        if pat.search(text):
            return True
    return bool(TRIVIAL_TO_CATASTROPHE.search(text))


def _check_absurd_noun_incongruity(text: str) -> bool:
    """True if serious framing pairs with absurd noun (ruled by cats, etc.)."""
    for m in INCONGRUITY_PATTERN.finditer(text):
        noun = m.group(1).lower()
        if noun in ABSURD_NOUNS:
            return True
    return False


def _check_contradiction_markers(text: str) -> bool:
    """True if text contains self-undermining satire markers."""
    lower = text.lower()
    return any(re.search(pat, lower) for pat in CONTRADICTION_MARKERS)


class SatireAnalyzer:
    """
    Heuristic satire/hyperbole detector.

    Identifies text that may be satirical based on:
    - Absurd outcome phrases
    - Disproportionate causation (minor cause -> catastrophic effect)
    - Semantic incongruity (serious + absurd noun)
    - Self-undermining contradiction markers

    Returns a probability estimate (0-1), not a certainty.
    """

    def analyze(self, text: str) -> tuple[float, list[SatireSignal], str]:
        """
        Analyze text for satire/hyperbole signals.

        Returns:
            (probability, signals, content_type_hint)
        """
        if not text or not text.strip():
            return 0.0, [], "Uncertain"

        signals: list[SatireSignal] = []
        score = 0.0

        # 1. Absurd outcome phrases (strong signal)
        absurd_count = _count_absurd_outcomes(text)
        if absurd_count > 0:
            sig_score = min(0.5 + absurd_count * 0.2, 0.9)
            signals.append(
                SatireSignal(
                    "Absurd outcome",
                    f"Phrases suggesting impossible or playful outcomes ({absurd_count} detected)",
                    sig_score,
                )
            )
            score = max(score, sig_score)

        # 2. Disproportionate causation (strong signal)
        if _check_disproportionate_causation(text):
            signals.append(
                SatireSignal(
                    "Disproportionate causation",
                    "Trivial cause linked to catastrophic/absurd effect",
                    0.75,
                )
            )
            score = max(score, 0.75)

        # 3. Semantic incongruity (ruled by cats, etc.)
        if _check_absurd_noun_incongruity(text):
            signals.append(
                SatireSignal(
                    "Semantic incongruity",
                    "Serious framing combined with absurd/impossible noun",
                    0.8,
                )
            )
            score = max(score, 0.8)

        # 4. Self-undermining contradiction
        if _check_contradiction_markers(text):
            signals.append(
                SatireSignal(
                    "Self-undermining",
                    "Position undermines itself (mocking/satirical structure)",
                    0.7,
                )
            )
            score = max(score, 0.7)

        # Cap and derive content type hint
        probability = min(score, 0.95)
        if probability >= 0.6:
            content_type = "Possibly Satire / Hyperbole"
        elif probability >= 0.35:
            content_type = "Uncertain (some satire signals)"
        else:
            content_type = "Genuine Argument (low satire probability)"

        return probability, signals, content_type
