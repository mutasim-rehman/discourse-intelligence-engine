"""Tone detection analyzer (keyword-based)."""

# Keyword sets per tone (skeleton; extend as needed)
URGENT = {"must", "need", "now", "urgent", "immediately", "critical", "crisis"}
DEFENSIVE = {"protect", "defend", "against", "threat", "attack", "stand for"}
FEAR_ORIENTED = {"fear", "afraid", "danger", "collapse", "destroy", "threat", "crisis"}


class ToneAnalyzer:
    """Detects tones: urgent, defensive, fear-oriented, etc."""

    def analyze(self, text: str) -> list[str]:
        """Return list of detected tone labels."""
        lower = text.lower()
        tones: list[str] = []
        if any(w in lower for w in URGENT):
            tones.append("Urgent")
        if any(w in lower for w in DEFENSIVE):
            tones.append("Defensive")
        if any(w in lower for w in FEAR_ORIENTED):
            tones.append("Fear-oriented")
        return tones
