"""Modal verb and pronoun framing analyzer."""

import re
from dataclasses import dataclass

MODAL_VERBS = {"must", "should", "could", "would", "might", "can", "will", "shall"}
PRONOUNS = ["we", "they", "us", "them", "i", "you"]


@dataclass
class ModalPronounResult:
    modal_verbs: list[str]
    pronoun_framing: dict[str, int]
    pronoun_insight: str | None


class ModalPronounAnalyzer:
    """Extracts modal verbs and pronoun usage for authority/framing analysis."""

    def analyze(self, text: str) -> ModalPronounResult:
        """Return modal verbs found, pronoun counts, and optional insight."""
        words = text.lower().split()
        modal_verbs: list[str] = []
        seen_modals: set[str] = set()
        for w in words:
            clean = re.sub(r"\W+", "", w)
            if clean in MODAL_VERBS and clean not in seen_modals:
                seen_modals.add(clean)
                modal_verbs.append(clean)

        pronoun_framing: dict[str, int] = {p: 0 for p in PRONOUNS}
        for w in words:
            clean = re.sub(r"\W+", "", w)
            if clean in pronoun_framing:
                pronoun_framing[clean] += 1

        # Only include non-zero pronouns in output (as in example)
        pronoun_framing = {k: v for k, v in pronoun_framing.items() if v > 0}

        # In-group/out-group insight if both "we" and "they" present
        insight: str | None = None
        if pronoun_framing.get("we", 0) + pronoun_framing.get("us", 0) >= 1:
            if pronoun_framing.get("they", 0) + pronoun_framing.get("them", 0) >= 1:
                insight = "Possible in-group / out-group framing"

        return ModalPronounResult(
            modal_verbs=modal_verbs,
            pronoun_framing=pronoun_framing,
            pronoun_insight=insight,
        )
