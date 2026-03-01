"""Heuristic satire and absurdity detection.

Detects text that may be satirical, hyperbolic, or parodic rather than
genuine persuasion. Uses the formula:

    Satire = (Hyperbole * Absurdity * Incongruity) / Context_Plausibility

Key insight: Real political/war rhetoric uses intense language too.
Satire requires SEMANTIC ABSURDITY (impossible outcomes) and/or
self-undermining incongruity - not just emotional intensity.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path


def _load_lexicon(lexicon_dir: Path, name: str) -> list:
    """Load a JSON lexicon file (list or dict)."""
    path = lexicon_dir / f"{name}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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

# === Policy plausibility ontology (Layer 2) ===
# Implausible policies: enforceable emotions, mandatory feelings
DEFAULT_IMPLAUSIBLE_POLICY_PATTERNS = [
    r"emotional\s+approval\s+ratings",
    r"gratitude\s+seminars",
    r"mandatory\s+optimism",
    r"weekly\s+emotional\s+rating",
    r"weekly\s+sentiment\s+rating",
    r"align\s+personal\s+feelings\s+with",
    r"disagreement\s+slows\s+development",
    r"mandatory\s+optimism\s+training",
    r"approval\s+ratings\s+for\s+government",
    r"score\s+above\s+\w*\s*satisfaction",
    r"mandatory\s+\w+\s+training",
    r"attendance\s+at\s+gratitude",
    r"require.*every\s+citizen.*(?:emotional|approval|rating)",
    r"submit\s+weekly\s+(?:emotional|approval)",
]

# Value terms for clash detection (claim to protect X, then restrict X)
VALUE_TERMS_FOR_CLASH = frozenset({
    "freedom", "democracy", "choice", "liberty", "rights", "free",
})
OBLIGATION_TERMS = frozenset({
    "require", "requires", "required", "mandatory", "must", "mandate",
})

# === CONTEXT PLAUSIBILITY: Real-world political/military discourse ===
# High density = plausible context = LOWER satire probability
GEOPOLITICAL_TERMS = frozenset({
    "iran", "russia", "china", "korea", "syria", "iraq", "afghanistan",
    "military", "troops", "forces", "combat", "operations", "missiles",
    "nuclear", "weapons", "terrorist", "proxies", "regime", "administration",
    "congress", "senate", "president", "commander", "homeland", "vessels",
    "international", "shipping", "naval", "attack", "strike",
})


def _implausible_policy_score(text: str, patterns: list) -> float:
    """0-1: Implausible policy phrases (enforceable emotions, mandatory feelings)."""
    if not patterns:
        return 0.0
    lower = text.lower()
    for pat in patterns:
        if isinstance(pat, str):
            try:
                if re.search(pat, lower, re.IGNORECASE):
                    return 0.7
            except re.error:
                if pat.lower() in lower:
                    return 0.7
    return 0.0


def _escalation_absurdity_score(text: str) -> float:
    """0-1: Universal scope + high-frequency + subjective measure = implausible."""
    lower = text.lower()
    has_universal = bool(re.search(r"\b(?:every|all|each)\s+(?:citizen|person|voter)\b", lower))
    has_frequent = bool(re.search(r"\b(?:weekly|daily|hourly)\b", lower))
    has_subjective = bool(re.search(r"\b(?:emotional|approval|sentiment|satisfaction|feelings?)\b", lower))
    if has_universal and has_frequent and has_subjective:
        return 0.75
    return 0.0


def _value_clash_score(text: str) -> float:
    """0-1: Claim to protect X (freedom) then propose policy that restricts X."""
    from discourse_engine.utils.text_utils import split_sentences

    sentences = split_sentences(text)
    if len(sentences) < 2:
        return 0.0

    # Value terms in first half
    first_half = " ".join(sentences[: len(sentences) // 2 + 1]).lower()
    words_first = set(re.findall(r"\b\w+\b", first_half))
    has_value = bool(words_first & VALUE_TERMS_FOR_CLASH)

    # Obligation in second half
    second_half = " ".join(sentences[len(sentences) // 2 :]).lower()
    words_second = set(re.findall(r"\b\w+\b", second_half))
    has_obligation = bool(words_second & OBLIGATION_TERMS)

    if has_value and has_obligation:
        return 0.65
    return 0.0


def _absurdity_score(text: str, implausible_patterns: list | None = None) -> float:
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

    # Policy plausibility ontology (Layer 2)
    patterns = implausible_patterns or DEFAULT_IMPLAUSIBLE_POLICY_PATTERNS
    score = max(score, _implausible_policy_score(text, patterns))

    # Escalation beyond plausible range
    score = max(score, _escalation_absurdity_score(text))

    return score


def _incongruity_score(text: str, value_clash: float = 0.0) -> float:
    """0-1: Self-undermining, internal contradiction, value clash."""
    lower = text.lower()
    base = 0.0
    if any(re.search(pat, lower) for pat in CONTRADICTION_MARKERS):
        base = 0.8
    return max(base, value_clash)


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
    - A = Absurdity (semantic impossibility, implausible policy, escalation)
    - I = Incongruity (self-undermining, value clash)
    - C = Context plausibility (real political/military discourse)

    War speeches have high H but low A and high C → low satire.
    """

    def __init__(self, lexicon_dir: Path | None = None) -> None:
        if lexicon_dir is None:
            lexicon_dir = Path(__file__).parent.parent / "lexicons"
        self.lexicon_dir = Path(lexicon_dir)
        raw = _load_lexicon(self.lexicon_dir, "implausible_policy_phrases")
        self._implausible_patterns = raw if isinstance(raw, list) else []

    def analyze(self, text: str) -> tuple[float, list[SatireSignal], str]:
        """
        Returns:
            (probability, signals, content_type_hint)
        """
        if not text or not text.strip():
            return 0.0, [], "Uncertain"

        H = _hyperbole_score(text)
        A = _absurdity_score(text, self._implausible_patterns)
        value_clash = _value_clash_score(text)
        I = _incongruity_score(text, value_clash)
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
