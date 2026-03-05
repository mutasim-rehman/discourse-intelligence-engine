"""Pattern-based logical fallacy detection."""

import re

from discourse_engine.models.report import FallacyFlag
from discourse_engine.scoring import fallacy_confidence
from discourse_engine.utils.text_utils import (
    sentence_containing_offset,
    split_sentences_with_offsets,
)

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

# Bandwagon: "everyone/we all/people say" as support
BANDWAGON_PATTERNS = [
    re.compile(
        r"\b(everyone|everybody|we all|all of us|no one|nobody|people (?:are saying|say))\b.*\b(know|knows|agree|agrees|support|supports|back|backs|love|loves|thrilled|understands|understand|believes|believe|aligned)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(the public|voters|the people|the crowd|the majority)\b.*\b(behind|support|backs|love|want)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\beveryone\s+(?:I\s+talk\s+to|who\s+[^.]+\b(?:is|are)\s+(?:thrilled|aligned|on board))\b",
        re.IGNORECASE,
    ),
]

# Straw man: misreporting or re-framing an opponent's view then knocking it down
STRAW_MAN_PATTERNS = [
    re.compile(
        r"\b(my|our)\s+opponent\s+(?:says|claims|argues)\b.*?\bbut\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bthey\s+(?:say|claim)\s+that\b.*?\bbut\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bsome\s+people\s+(?:say|claim|believe)\b.*?\bbut\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # "By calling it X, you are saying Y" → re-frame critic's wording into an extreme stance.
    re.compile(
        r"\bby\s+calling\s+(?:it|this)\s+[^,]+,\s*[\"']?\s*you\s+are\s+(?:essentially\s+)?saying\b",
        re.IGNORECASE,
    ),
    # "By focusing on X, you are essentially saying Y" → reframe critic's concern into extreme stance.
    re.compile(
        r"\bby\s+(?:focusing|fixating)\s+on\s+[^,]+,\s*you\s+are\s+(?:essentially\s+)?saying\b",
        re.IGNORECASE,
    ),
    # "What it actually is, is ..." → rebrand the criticized object into a noble-sounding one.
    re.compile(
        r"\bwhat\s+it\s+actually\s+is,\s+is\b",
        re.IGNORECASE,
    ),
    # "What I've confirmed is X" → replace question's negative framing with positive reframe (Straw Man).
    re.compile(
        r"\bwhat\s+I(?:'ve|\s+have)\s+confirmed\s+is\b",
        re.IGNORECASE,
    ),
]

# Red herring: explicit topic-shift markers
RED_HERRING_PATTERNS = [
    re.compile(
        r"\b(the real issue|the real question|what really matters|what truly matters|more importantly|let's talk about)\b",
        re.IGNORECASE,
    ),
]

# Appeal to authority: unnamed or vague authorities as justification
APPEAL_TO_AUTHORITY_PATTERNS = [
    re.compile(
        r"\bexperts?\s+agree\b", re.IGNORECASE
    ),
    re.compile(
        r"\bscientists\s+(?:say|tell us|agree)\b", re.IGNORECASE
    ),
    re.compile(
        r"\bstudies\s+show\b", re.IGNORECASE
    ),
    re.compile(
        r"\bresearch\s+(?:shows|says|tells us)\b", re.IGNORECASE
    ),
    re.compile(
        r"\bthe science\s+is\s+settled\b", re.IGNORECASE
    ),
]

# Hasty generalization: small sample → broad claim
HASTY_GENERALIZATION_PATTERNS = [
    re.compile(
        r"\b(I|we)\s+(?:met|know|talked to|spoke to)\s+(?:a|one|a few)\s+\w+.*?\bthey\b.*?\b(all|always|never)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bfrom\s+(?:one|a few|a couple)\s+\w+.*?\bwe\b.*?\b(can|could)\s+see\b",
        re.IGNORECASE | re.DOTALL,
    ),
]

# Circular reasoning: conclusion reused as premise
CIRCULAR_CONNECTORS = re.compile(r"\b(because|since)\b", re.IGNORECASE)

# Slippery slope: escalating chain of consequences
SLIPPERY_SLOPE_ESCALATION_MARKERS = (
    "next we'll",
    "next we will",
    "eventually",
    "soon",
    "every time",
    "is to suggest",
    "keep us in",
    "leave us in",
)
SLIPPERY_SLOPE_EXTREME_TERMS = (
    "collapse",
    "crumble",
    "dark room",
    "dark, silent nation",
    "dark ages",
    "lose our freedom",
    "death",
    "at the mercy of foreign powers",
    "pile of rust",
    "stone age",
    "lawless wasteland",
    "broken workforce",
)


def _clause_similarity(left: str, right: str) -> float:
    """Very lightweight bag-of-words similarity for circular reasoning."""
    left_words = set(re.findall(r"\b[a-z]{2,}\b", left.lower()))
    right_words = set(re.findall(r"\b[a-z]{2,}\b", right.lower()))
    if not left_words or not right_words:
        return 0.0
    overlap = len(left_words & right_words)
    return overlap / ((len(left_words) * len(right_words)) ** 0.5)


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

# Coercive choice: "Shall we X, or do we need to Y?"
COERCIVE_CHOICE_PATTERN = re.compile(
    r"\bshall\s+we\s+[^?]+?\s+or\s+do\s+we\s+need\s+to\s+[^?]+\?",
    re.IGNORECASE,
)
# False dilemma without "either": "Are we going to X or Y?" / "trust X or Y"
FALSE_DILEMMA_OR_CHOICE_PATTERN = re.compile(
    r"\b(?:are we going to|shall we|trust|focus on|talk about)\s+.+?\s+or\s+(?:are we|your|we)\s+",
    re.IGNORECASE,
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
        sentences_with_offsets = split_sentences_with_offsets(text)

        def _sentence_at(match: re.Match) -> str:
            return sentence_containing_offset(sentences_with_offsets, match.start())

        # False dilemma patterns
        m = FALSE_DILEMMA_PATTERN.search(text)
        if m and not _is_genuine_dichotomy(text):
            conf = fallacy_confidence(0.8)
            flags.append(
                FallacyFlag(
                    "False Dilemma",
                    "pattern: either X or Y",
                    _sentence_at(m),
                    confidence=conf,
                    fallacy_type="false_dilemma",
                )
            )

        m = COERCIVE_CHOICE_PATTERN.search(text)
        if m:
            conf = fallacy_confidence(0.8, extra_signals=1)
            flags.append(
                FallacyFlag(
                    "False Dilemma",
                    "coercive choice: 'Shall we X, or do we need to Y?'",
                    _sentence_at(m),
                    confidence=conf,
                    fallacy_type="false_dilemma",
                )
            )

        m = FALSE_DILEMMA_OR_CHOICE_PATTERN.search(text)
        if m and not _is_genuine_dichotomy(text):
            conf = fallacy_confidence(0.72)
            flags.append(
                FallacyFlag(
                    "False Dilemma",
                    "forced choice: 'Are we going to X or Y?' / 'trust X or Y'",
                    _sentence_at(m),
                    confidence=conf,
                    fallacy_type="false_dilemma",
                )
            )

        # Appeal to fear
        if any(t in lower for t in FEAR_TERMS):
            fear_match = next(
                (re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE) for t in FEAR_TERMS if t in lower),
                None,
            )
            sent = (
                _sentence_at(fear_match)
                if fear_match
                else (sentences_with_offsets[0][0] if sentences_with_offsets else "")
            )
            conf = fallacy_confidence(0.65)
            flags.append(
                FallacyFlag(
                    "Appeal to Fear",
                    "threat language",
                    sent,
                    confidence=conf,
                    fallacy_type="appeal_to_fear",
                )
            )

        # Ad hominem / attack
        for pat in ATTACK_PATTERNS:
            m = pat.search(text)
            if m:
                conf = fallacy_confidence(0.75)
                flags.append(
                    FallacyFlag(
                        "Ad Hominem / Attack",
                        "they want to [verb] pattern",
                        _sentence_at(m),
                        confidence=conf,
                        fallacy_type="ad_hominem",
                    )
                )
                break

        # Bandwagon
        for pat in BANDWAGON_PATTERNS:
            m = pat.search(text)
            if m:
                conf = fallacy_confidence(0.72, extra_signals=1)
                flags.append(
                    FallacyFlag(
                        "Bandwagon",
                        "appeal to popularity / 'everyone agrees' pattern",
                        _sentence_at(m),
                        confidence=conf,
                        fallacy_type="bandwagon",
                    )
                )
                break

        # Straw man (heuristic)
        for pat in STRAW_MAN_PATTERNS:
            m = pat.search(text)
            if m:
                conf = fallacy_confidence(0.7)
                flags.append(
                    FallacyFlag(
                        "Straw Man",
                        "opponent's view re-framed then rejected (e.g. 'X says that..., but ...' or 'By calling it X you are saying Y')",
                        _sentence_at(m),
                        confidence=conf,
                        fallacy_type="straw_man",
                    )
                )
                break

        # Red herring: explicit topic shift phrases
        for pat in RED_HERRING_PATTERNS:
            m = pat.search(text)
            if m:
                conf = fallacy_confidence(0.65)
                flags.append(
                    FallacyFlag(
                        "Red Herring",
                        "topic shift marker ('the real issue', 'what really matters', etc.)",
                        _sentence_at(m),
                        confidence=conf,
                        fallacy_type="red_herring",
                    )
                )
                break

        # Appeal to authority
        for pat in APPEAL_TO_AUTHORITY_PATTERNS:
            m = pat.search(text)
            if m:
                conf = fallacy_confidence(0.7)
                flags.append(
                    FallacyFlag(
                        "Appeal to Authority",
                        "vague or unnamed authority used as justification",
                        _sentence_at(m),
                        confidence=conf,
                        fallacy_type="appeal_to_authority",
                    )
                )
                break

        # Hasty generalization
        for pat in HASTY_GENERALIZATION_PATTERNS:
            m = pat.search(text)
            if m:
                conf = fallacy_confidence(0.68)
                flags.append(
                    FallacyFlag(
                        "Hasty Generalization",
                        "small sample generalized to broad claim",
                        _sentence_at(m),
                        confidence=conf,
                        fallacy_type="hasty_generalization",
                    )
                )
                break

        # Circular reasoning
        for sentence, _start, _end in sentences_with_offsets:
            if not CIRCULAR_CONNECTORS.search(sentence):
                continue
            parts = CIRCULAR_CONNECTORS.split(sentence, maxsplit=1)
            if len(parts) != 2:
                continue
            left, right = parts[0], parts[1]
            sim = _clause_similarity(left, right)
            if sim >= 0.65:
                conf = fallacy_confidence(0.75, extra_signals=1)
                flags.append(
                    FallacyFlag(
                        "Circular Reasoning",
                        "premise and conclusion share nearly identical content around 'because/since'",
                        sentence,
                        confidence=conf,
                        fallacy_type="circular_reasoning",
                    )
                )
                break

        # Slippery slope via explicit escalation chain in a single sentence
        for sentence, _start, _end in sentences_with_offsets:
            lower_sent = sentence.lower()
            conditional_trigger = (
                "if we" in lower_sent
                or "to suggest we" in lower_sent
                or "to suggest that" in lower_sent
                or (
                    any(term in lower_sent for term in SLIPPERY_SLOPE_EXTREME_TERMS)
                    and ("keep us in" in lower_sent or "leave us in" in lower_sent or "return to" in lower_sent)
                )
            )
            if not conditional_trigger:
                continue
            if not any(marker in lower_sent for marker in SLIPPERY_SLOPE_ESCALATION_MARKERS):
                continue
            if not any(term in lower_sent for term in SLIPPERY_SLOPE_EXTREME_TERMS):
                continue
            conf = fallacy_confidence(0.78, extra_signals=2)
            flags.append(
                FallacyFlag(
                    "Slippery Slope",
                    "chain of escalating consequences ('if we ... then/next ... eventually ...')",
                    sentence,
                    confidence=conf,
                    fallacy_type="slippery_slope",
                )
            )
            break

        # Slippery slope via logical leaps (problem → catastrophic solution with low similarity)
        try:
            from discourse_engine.v3.narrative_arc import compute_logical_leaps

            leaps = compute_logical_leaps(text)
        except Exception:
            leaps = []

        for ll in leaps:
            pattern_hint = (
                f"logical leap from problem to solution with low similarity (score={ll.similarity:.2f})"
            )
            conf = fallacy_confidence(0.7, extra_signals=1)
            # We only have sentence indices here; LogicalLeap already carries snippets
            sentence = ll.solution_snippet
            flags.append(
                FallacyFlag(
                    "Slippery Slope / Non-Sequitur",
                    pattern_hint,
                    sentence,
                    confidence=conf,
                    fallacy_type="slippery_slope",
                )
            )
            if len(flags) > 10:
                break

        return flags
