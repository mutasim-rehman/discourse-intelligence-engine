"""Rule-based hidden assumption extraction."""

import re
from dataclasses import dataclass

from discourse_engine.models.report import AssumptionFlag
from discourse_engine.utils.text_utils import split_sentences

# ---------------------------------------------------------------------------
# Presupposition triggers (linguistic constructions that imply unstated beliefs)
# ---------------------------------------------------------------------------

# Factive verbs: presuppose their complement is true (e.g. "realized X" assumes X)
FACTIVE_VERBS = frozenset({
    "know", "knew", "knows", "realize", "realized", "realizes",
    "discover", "discovered", "discovers", "regret", "regrets", "regretted",
    "acknowledge", "acknowledged", "acknowledges", "admit", "admits", "admitted",
    "recognize", "recognized", "recognizes", "notice", "noticed", "notices",
})

# Implicative verbs: imply an unstated prior (e.g. "managed to" implies attempted)
IMPLICATIVE_VERBS = frozenset({
    "manage", "managed", "manages", "avoid", "avoided", "avoids",
    "forget", "forgot", "forgets", "forgotten", "happen", "happened", "happens",
})

# Change-of-state verbs: presuppose prior state (e.g. "continued" implies before)
CHANGE_OF_STATE_VERBS = frozenset({
    "begin", "began", "begins", "start", "started", "starts",
    "stop", "stopped", "stops", "continue", "continued", "continues",
    "resume", "resumed", "resumes", "leave", "left", "leaves",
    "arrive", "arrived", "arrives",
})

# Repetition/iteration: presuppose prior occurrence
REPETITION_WORDS = frozenset({"again", "still", "return", "returned", "restore", "restored"})

# Epistemic shortcuts: present claim as obvious without justification
EPISTEMIC_SHORTCUTS = frozenset({
    "obviously", "clearly", "certainly", "of course", "needless to say",
    "it goes without saying", "as we all know", "everyone knows",
    "everybody knows", "as everyone knows", "self-evident", "evidently",
})

# Universal quantifiers: imply shared belief or blanket claim
UNIVERSAL_QUANTIFIERS = frozenset({
    "everyone", "everybody", "nobody", "no one", "always", "never",
    "all", "none", "anyone", "anybody",
})

# Vague authority: invokes unspecified support
VAGUE_AUTHORITY_PATTERNS = (
    re.compile(r"\bexperts?\b", re.IGNORECASE),
    re.compile(r"\bstudies?\s+(?:show|suggest|indicate|find)", re.IGNORECASE),
    re.compile(r"\bmany\s+(?:people|believe|say|think)", re.IGNORECASE),
    re.compile(r"\b(?:some|most)\s+people\s+(?:believe|say|think)", re.IGNORECASE),
    re.compile(r"\b(?:it['\u2019]?s\s+)?widely\s+(?:known|believed|accepted)\b", re.IGNORECASE),
    re.compile(r"\bthe\s+people\b", re.IGNORECASE),
    re.compile(r"\bresearch\s+(?:shows|suggests|indicates)\b", re.IGNORECASE),
)

# Conclusion markers: suggest inference without full premises (enthymeme)
CONCLUSION_MARKERS = re.compile(
    r"\b(therefore|thus|hence|so|consequently)\b",
    re.IGNORECASE,
)

# Loaded/suggestive questions: "Why do you still X?", "When did you stop X?"
LOADED_QUESTION_PATTERNS = (
    re.compile(r"\bwhy\s+do\s+you\s+still\s+", re.IGNORECASE),
    re.compile(r"\bwhen\s+did\s+you\s+stop\s+", re.IGNORECASE),
    re.compile(r"\bhow\s+(?:could|can)\s+you\s+(?:possibly\s+)?", re.IGNORECASE),
    re.compile(r"\bis\s+\w+\s+(?:really|actually)\s+(?:so|that)\s+", re.IGNORECASE),
)

# Suggestive questioning: stacked alternatives implying negative
SUGGESTIVE_QUESTION_PATTERN = re.compile(
    r"\bis\s+(?:he|she|they|it)\s+(?:\w+\s+)?(?:or\s+)?(?:\w+\s+)?\?",
    re.IGNORECASE,
)


def _get_words_lower(text: str) -> set[str]:
    """Return set of lowercased words in text."""
    return set(re.findall(r"\b[a-z]+\b", text.lower()))


HEDGING_WORDS = frozenset({"perhaps", "maybe", "might", "could", "possibly", "sometimes", "allegedly"})


def _hedging_penalty(sentence: str) -> float:
    """Reduce confidence if sentence contains hedging (0 or 0.1)."""
    lower = sentence.lower()
    words = set(re.findall(r"\b\w+\b", lower))
    return 0.1 if (words & HEDGING_WORDS) else 0.0


@dataclass
class _AssumptionMatch:
    """Internal: a detected assumption with trigger, sentence, and base confidence."""

    description: str
    trigger: str | None
    sentence: str
    confidence: float


def _check_presupposition_triggers(sentence: str) -> list[_AssumptionMatch]:
    """Check for presupposition-triggering language."""
    matches: list[_AssumptionMatch] = []
    lower = sentence.lower()
    words = _get_words_lower(sentence)

    base = 0.75 - _hedging_penalty(sentence)
    for w in FACTIVE_VERBS:
        if w in words or f"{w}s " in lower or f" {w} " in lower or f" {w}ed " in lower:
            matches.append(_AssumptionMatch(
                "Presupposition: treats something as already established (factive verb)",
                w, sentence, base,
            ))
            break

    base = 0.65 - _hedging_penalty(sentence)
    for w in IMPLICATIVE_VERBS:
        if w in words:
            matches.append(_AssumptionMatch(
                "Presupposition: implies unstated prior action or attempt (implicative verb)",
                w, sentence, base,
            ))
            break

    base = 0.68 - _hedging_penalty(sentence)
    for w in CHANGE_OF_STATE_VERBS:
        if w in words:
            matches.append(_AssumptionMatch(
                "Presupposition: assumes a prior state (change-of-state verb)",
                w, sentence, base,
            ))
            break

    base = 0.70 - _hedging_penalty(sentence)
    for w in REPETITION_WORDS:
        if re.search(rf"\b{w}\b", lower):
            matches.append(_AssumptionMatch(
                "Presupposition: implies prior occurrence (repetition/iteration)",
                w, sentence, base,
            ))
            break

    return matches


def _check_epistemic_shortcuts(sentence: str) -> list[_AssumptionMatch]:
    """Check for epistemic shortcuts (obviously, clearly, etc.)."""
    matches: list[_AssumptionMatch] = []
    lower = sentence.lower()

    base = 0.80 - _hedging_penalty(sentence)
    for phrase in EPISTEMIC_SHORTCUTS:
        if phrase in lower:
            matches.append(_AssumptionMatch(
                "Presents claim as obvious without justification (epistemic shortcut)",
                phrase, sentence, base,
            ))
            break

    return matches


def _check_universal_quantifiers(sentence: str) -> list[_AssumptionMatch]:
    """Check for universal quantifiers implying blanket claims."""
    matches: list[_AssumptionMatch] = []
    words = _get_words_lower(sentence)

    base = 0.55 - _hedging_penalty(sentence)
    for w in UNIVERSAL_QUANTIFIERS:
        if w in words:
            matches.append(_AssumptionMatch(
                "Unstated universal claim: implies shared belief or blanket generalization",
                w, sentence, base,
            ))
            break

    return matches


def _check_vague_authority(sentence: str) -> list[_AssumptionMatch]:
    """Check for vague authority without specification."""
    matches: list[_AssumptionMatch] = []
    base = 0.65 - _hedging_penalty(sentence)
    for pat in VAGUE_AUTHORITY_PATTERNS:
        m = pat.search(sentence)
        if m:
            matches.append(_AssumptionMatch(
                "Vague authority invoked without specification",
                m.group(0)[:30], sentence, base,
            ))
            break
    return matches


def _check_conclusion_markers(sentence: str) -> list[_AssumptionMatch]:
    """Check for conclusion markers (enthymeme). 'Therefore/thus' = higher conf than 'so'."""
    matches: list[_AssumptionMatch] = []
    m = CONCLUSION_MARKERS.search(sentence)
    if m:
        marker = m.group(1).lower()
        base = 0.70 if marker in ("therefore", "thus", "hence") else 0.55
        base -= _hedging_penalty(sentence)
        matches.append(_AssumptionMatch(
            "Conclusion marker suggests inference without full stated premises (enthymeme)",
            m.group(1), sentence, base,
        ))
    return matches


def _check_loaded_questions(sentence: str) -> list[_AssumptionMatch]:
    """Check for loaded or suggestive questions."""
    matches: list[_AssumptionMatch] = []
    if "?" not in sentence:
        return matches

    base = 0.85 - _hedging_penalty(sentence)
    for pat in LOADED_QUESTION_PATTERNS:
        if pat.search(sentence):
            matches.append(_AssumptionMatch(
                "Loaded question: implies an assumption in the question itself",
                None, sentence, base,
            ))
            return matches

    base = 0.75 - _hedging_penalty(sentence)
    if SUGGESTIVE_QUESTION_PATTERN.search(sentence):
        matches.append(_AssumptionMatch(
            "Suggestive question: stacked alternatives implying negative traits",
            None, sentence, base,
        ))

    return matches


class HiddenAssumptionExtractor:
    """
    Extracts hidden assumptions via rule-based pattern matching.
    Detects presuppositions, enthymemes, epistemic shortcuts, loaded questions,
    and vague authority references.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4") -> None:
        """
        Initialize the extractor.
        api_key and model are kept for API compatibility but ignored in rule-based mode.
        """
        self.api_key = api_key
        self.model = model

    def analyze(self, text: str) -> list[AssumptionFlag]:
        """
        Extract hidden assumptions from text using rule-based patterns.
        Returns a list of AssumptionFlag with description and source sentence.
        """
        if not text or not text.strip():
            return []

        sentences = split_sentences(text)
        all_matches: list[_AssumptionMatch] = []

        for sentence in sentences:
            all_matches.extend(_check_presupposition_triggers(sentence))
            all_matches.extend(_check_epistemic_shortcuts(sentence))
            all_matches.extend(_check_universal_quantifiers(sentence))
            all_matches.extend(_check_vague_authority(sentence))
            all_matches.extend(_check_conclusion_markers(sentence))
            all_matches.extend(_check_loaded_questions(sentence))

        # Deduplicate by full description (keep first occurrence)
        seen: set[str] = set()
        result: list[AssumptionFlag] = []
        for m in all_matches:
            full = f"{m.description} [trigger: '{m.trigger}']" if m.trigger else m.description
            if full not in seen:
                seen.add(full)
                conf = max(0.0, min(0.95, m.confidence))
                result.append(AssumptionFlag(description=full, sentence=m.sentence, confidence=conf))

        return result
