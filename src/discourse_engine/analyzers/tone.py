"""Tone detection analyzer (multi-feature weighted scoring).

Tone is computed from verb intensity, emotional lexicon, imperative density,
threat markers, plausible-deniability patterns, and structural signals.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discourse_engine.models.report import AgendaFlag, AssumptionFlag, TriggerProfile

# Plausible deniability: [First Person] + [Epistemic Hedge] + [Negative Polarity]
PLAUSIBLE_DENIABILITY = re.compile(
    r"\b(?:I'm|I am|we're|we are|I|we)\s+(?:sure|hope|believe|trust|assume)\s+"
    r"(?:you|they|he|she|it)\s+(?:didn't|wouldn't|won't|couldn't|shouldn't)\b",
    re.IGNORECASE,
)
OBLIGATION_MODAL = re.compile(
    r"\b(?:should|must|need\s+to|ought\s+to|have\s+to)\b",
    re.IGNORECASE,
)
SOFT_MODAL = re.compile(r"\b(?:would|might|may)\b", re.IGNORECASE)
EPISTEMIC_IN_TEXT = re.compile(r"\bobviously|clearly|certainly\b", re.IGNORECASE)

# Corporate jargon terms for Clinical tone (Jargon_Density)
JARGON_TERMS = frozenset({
    "right-sizing", "decoupling", "headcount", "harmonization",
    "bandwidth", "synergy", "pivot", "streamline", "initiative",
    "trajectory", "frictionless", "optimize", "strategic", "stakeholder",
    "leverage", "paradigm", "ecosystem", "throughput", "operational",
    "workforce", "scalable", "alignment", "resources",
})

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
    """Detects tones using multi-feature scoring and structural signals."""

    def analyze(
        self,
        text: str,
        *,
        word_count: int | None = None,
        trigger_profile: "TriggerProfile | None" = None,
        hidden_assumptions: "list[AssumptionFlag] | None" = None,
        hidden_agenda_flags: "list[AgendaFlag] | None" = None,
        modal_verbs: list[str] | None = None,
        pronoun_framing: dict | None = None,
    ) -> list[str]:
        """Return list of detected tone labels."""
        if not text or not text.strip():
            return []
        lower = text.lower()
        words = text.split()
        wc = word_count if word_count is not None else len(words)
        tones: list[str] = []

        # Urgent
        if _urgent_score(text) >= 0.35:
            tones.append("Urgent")
        if any(w in lower for w in DEFENSIVE):
            tones.append("Defensive")
        if any(w in lower for w in FEAR_ORIENTED):
            tones.append("Fear-oriented")

        # Passive-aggressive: (1) regex, or (2) structural: You + Epistemic Shortcut + Would/Might
        if PLAUSIBLE_DENIABILITY.search(text) and OBLIGATION_MODAL.search(text):
            tones.append("Passive-aggressive")
        elif (
            pronoun_framing and pronoun_framing.get("you", 0) >= 1
            and EPISTEMIC_IN_TEXT.search(text)
            and SOFT_MODAL.search(text)
            and (hidden_assumptions and any("obviously" in a.description.lower() or "epistemic" in a.description.lower() for a in hidden_assumptions))
        ):
            tones.append("Passive-aggressive")

        # Corporate/Clinical: word_count > 50, jargon_density > 10% OR 3+ Obscuration flags, fear Low
        if wc > 50 and trigger_profile and trigger_profile.fear_level == "Low":
            obscuration_count = sum(1 for f in (hidden_agenda_flags or []) if getattr(f, "family", "") == "Obscuration")
            word_set = {re.sub(r"\W", "", w).lower() for w in words if len(w) > 2}
            jargon_count = len(word_set & JARGON_TERMS)
            jargon_density = jargon_count / wc if wc else 0
            if jargon_density >= 0.10 or obscuration_count >= 3:
                tones.append("Corporate/Clinical")

        return tones
