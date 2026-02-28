"""Pattern-based logical fallacy detection."""

import re

from discourse_engine.models.report import FallacyFlag

# False dilemma: "either X or Y" — but NOT when Y = not-X (genuine dichotomy)
FALSE_DILEMMA_PATTERN = re.compile(
    r"\beither\b.*\bor\b", re.IGNORECASE | re.DOTALL
)
# Capture "either X or Y" to extract the second option
EITHER_OR_CAPTURE = re.compile(
    r"\beither\b(.+?)\bor\b(.+)$", re.IGNORECASE | re.DOTALL
)
# Genuine dichotomy: second option negates the first (X vs not-X)
# These match within the second clause (text after "or")
GENUINE_DICHOTOMY_PATTERNS = (
    re.compile(
        r"\b(doesn't|don't|isn't|aren't|wasn't|weren't|won't|can't|couldn't|"
        r"shouldn't|wouldn't|hasn't|haven't|hadn't|mustn't)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnot\b", re.IGNORECASE),
    re.compile(r"\bno\b(?!\s+one|\s+longer)", re.IGNORECASE),
    re.compile(r"\bnever\b", re.IGNORECASE),
)
# Complementary pairs: both options exhaust the space
COMPLEMENTARY_PAIRS = frozenset(
    {
        ("true", "false"),
        ("false", "true"),
        ("yes", "no"),
        ("no", "yes"),
    }
)


def _is_genuine_dichotomy(text: str) -> bool:
    """Return True if 'either X or Y' expresses a genuine dichotomy (X vs not-X)."""
    m = EITHER_OR_CAPTURE.search(text)
    if not m:
        return False
    first = m.group(1).strip().rstrip(".,;:!?").lower()
    second = m.group(2).strip().rstrip(".,;:!?").lower()
    # Check for negation in second option (doesn't, isn't, not, etc.)
    if any(pat.search(second) for pat in GENUINE_DICHOTOMY_PATTERNS):
        return True
    # Check for complementary pairs (true/false, yes/no)
    first_word = first.split()[-1] if first else ""
    second_word = second.split()[0] if second else ""
    if (first_word, second_word) in COMPLEMENTARY_PAIRS:
        return True
    return False


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

        if FALSE_DILEMMA_PATTERN.search(text) and not _is_genuine_dichotomy(text):
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
