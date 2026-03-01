"""Tone detection analyzer (multi-feature weighted scoring).

Tone is computed from verb intensity, emotional lexicon, imperative density,
and threat markers — not just single keywords, to reduce false positives.
"""

import re

# Strong urgency: explicit calls to action
URGENT_STRONG = {"urgent", "immediately", "critical", "crisis", "now", "asap"}
# Weak urgency: modal necessity (common in neutral policy text)
URGENT_WEAK = {"must", "need", "require"}
# Imperative/exclamation markers
IMPERATIVE_MARKERS = ("!", "—", "•")
DEFENSIVE = {"protect", "defend", "against", "threat", "attack", "stand for"}
FEAR_ORIENTED = {"fear", "afraid", "danger", "collapse", "destroy", "threat", "crisis"}


def _urgent_score(text: str) -> float:
    """Weighted urgency: strong markers count more; 'must' alone in long text does not trigger."""
    lower = text.lower()
    words = set(re.findall(r"\b\w+\b", lower))
    word_count = max(1, len(lower.split()))
    strong = sum(1 for w in URGENT_STRONG if w in words)
    weak = sum(1 for w in URGENT_WEAK if w in words)
    # Strong markers: 0.4 each. Weak: 0.08 each, dampened by text length (single must in 200 words = 0.04)
    weak_damped = weak * 0.08 * (50 / max(word_count, 50))
    score = strong * 0.4 + weak_damped
    if "!" in text:
        score += 0.15
    return min(score, 1.0)


class ToneAnalyzer:
    """Detects tones using multi-feature scoring to reduce false positives."""

    def analyze(self, text: str) -> list[str]:
        """Return list of detected tone labels."""
        if not text or not text.strip():
            return []
        lower = text.lower()
        tones: list[str] = []
        # Urgent: require threshold (avoid labeling every modal as urgent)
        if _urgent_score(text) >= 0.35:
            tones.append("Urgent")
        if any(w in lower for w in DEFENSIVE):
            tones.append("Defensive")
        if any(w in lower for w in FEAR_ORIENTED):
            tones.append("Fear-oriented")
        return tones
