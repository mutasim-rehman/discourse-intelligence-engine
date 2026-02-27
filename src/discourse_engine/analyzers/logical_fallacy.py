"""Pattern-based logical fallacy detection."""

import re

from discourse_engine.models.report import FallacyFlag

# False dilemma: "either X or Y"
FALSE_DILEMMA_PATTERN = re.compile(
    r"\beither\b.*\bor\b", re.IGNORECASE | re.DOTALL
)
# Appeal to fear: threat language
FEAR_TERMS = {"collapse", "destroy", "threat", "danger", "catastrophe", "crisis"}
# Ad hominem / attack: "they want to destroy"
ATTACK_PATTERNS = [
    re.compile(r"\bthey\s+want\s+to\s+\w+", re.IGNORECASE),
]


class LogicalFallacyAnalyzer:
    """Flags possible logical fallacies via pattern matching."""

    def analyze(self, text: str) -> list[FallacyFlag]:
        """Return list of FallacyFlag for detected patterns."""
        flags: list[FallacyFlag] = []
        lower = text.lower()

        if FALSE_DILEMMA_PATTERN.search(text):
            flags.append(FallacyFlag("False Dilemma", "pattern: either X or Y"))

        if any(t in lower for t in FEAR_TERMS):
            flags.append(FallacyFlag("Appeal to Fear", "threat language"))

        for pat in ATTACK_PATTERNS:
            if pat.search(text):
                flags.append(
                    FallacyFlag("Ad Hominem / Attack", "they want to [verb] pattern")
                )
                break

        return flags
