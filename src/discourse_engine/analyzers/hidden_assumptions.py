"""Rule-based hidden assumption extraction."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from discourse_engine.models.report import AssumptionFlag
from discourse_engine.utils.text_utils import split_sentences


def _load_lexicon(lexicon_dir: Path, name: str) -> list[str]:
    """Load a JSON lexicon file."""
    path = lexicon_dir / f"{name}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []

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
# NOTE: "none" removed from simple match - use NONE_OF_X_PATTERN instead
UNIVERSAL_QUANTIFIERS = frozenset({
    "everyone", "everybody", "nobody", "no one", "always", "never",
    "all", "anyone", "anybody",
})

# "None of X are Y" - structurally meaningful universal negation over X
# Exclude meta-framing: "presented as", "described as" (author clarifying scope, not asserting)
NONE_OF_X_PATTERN = re.compile(
    r"\bnone\s+of\s+(?:these|those|the)\s+\w+(?:\s+\w+)?\s+(?:are|is|were|was)\b",
    re.IGNORECASE,
)
META_FRAMING_SUPPRESS = re.compile(
    r"\b(?:presented|described|portrayed|characterized|framed)\s+as\b",
    re.IGNORECASE,
)

# Meta-discussion: "The word 'X' is often used" - don't flag trigger X as assumption
META_DISCUSSION_PATTERN = re.compile(
    r"\b(?:the\s+)?(?:word|term|phrase)\s+['\"]?\w+['\"]?\s+(?:is|are|can be)",
    re.IGNORECASE,
)

# Reporting verbs (Step 7): sentence describes/analyzes discourse, not author's claim
REPORTING_VERBS = frozenset({
    "argues", "argued", "claims", "claimed", "states", "stated", "describes",
    "described", "suggests", "suggested", "notes", "noted", "observes",
    "observed", "reports", "reported", "according to", "as X said",
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

# ---------------------------------------------------------------------------
# Structural assumption patterns (Layer 2)
# ---------------------------------------------------------------------------

# Necessity modal + outcome: Entity must/need to/require Action to/for Outcome
NECESSITY_MODAL_OUTCOME = re.compile(
    r"\b(\w+(?:\s+\w+){0,3})\s+(?:must|need\s+to|needs\s+to|require|requires|has\s+to|have\s+to|should)\s+"
    r"(\w+(?:\s+\w+){0,4})\s+(?:to|for)\s+(\w+(?:\s+\w+){0,2})\b",
    re.IGNORECASE,
)

# Conditional necessity: if/when X, (then) we must/need to/should
CONDITIONAL_NECESSITY = re.compile(
    r"\b(if|when)\s+[^,]+,\s+(?:then\s+)?(?:we\s+)?(?:must|need\s+to|needs\s+to|should)\b",
    re.IGNORECASE,
)

# Without X, Y: without X ... collapse/fail/impossible/cannot
WITHOUT_X_Y = re.compile(
    r"\bwithout\s+(\w+(?:\s+\w+){0,2}).*?(collapse|fail|impossible|cannot|stagnat\w*)",
    re.IGNORECASE | re.DOTALL,
)

# Causal claims: X leads to/results in/causes Y - causation may be assumed, not proven
CAUSAL_LEADS_TO = re.compile(
    r"\b(\w+(?:\s+\w+){0,2})\s+(?:leads?\s+to|results?\s+in|causes?)\s+(\w+(?:\s+\w+){0,3})",
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


def _compute_density_factor(text: str) -> float:
    """Return 0.95--1.05 multiplier: more rhetorical signals -> higher confidence."""
    lower = text.lower()
    signals = sum(1 for _ in re.finditer(r"\b(must|should|require|therefore|obviously|everyone|nobody)\b", lower))
    word_count = max(1, len(text.split()))
    # 1+ signal per 50 words -> small boost
    density = signals / (word_count / 50)
    if density >= 2:
        return 1.05
    if density >= 1:
        return 1.02
    if density < 0.3 and signals == 1:
        return 0.97  # single trigger in long neutral text
    return 1.0


def _apply_suppressions(base_conf: float, sentence: str, density_factor: float) -> float:
    """Apply meta-discussion suppression and density adjustment."""
    conf = base_conf * density_factor
    if META_DISCUSSION_PATTERN.search(sentence):
        conf *= 0.5  # meta-discussion about a word, not use of it
    return max(0.0, min(0.95, conf))


@dataclass
class _AssumptionMatch:
    """Internal: Layer A structural detection with type for calibrated scoring."""

    description: str
    trigger: str | None
    sentence: str
    detection_type: str  # For calibrated scoring
    raw_confidence: float  # Legacy; superseded by calibrated score


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
                w, sentence, "factive", base,
            ))
            break

    base = 0.65 - _hedging_penalty(sentence)
    for w in IMPLICATIVE_VERBS:
        if w in words:
            matches.append(_AssumptionMatch(
                "Presupposition: implies unstated prior action or attempt (implicative verb)",
                w, sentence, "implicative", base,
            ))
            break

    base = 0.68 - _hedging_penalty(sentence)
    for w in CHANGE_OF_STATE_VERBS:
        if w in words:
            matches.append(_AssumptionMatch(
                "Presupposition: assumes a prior state (change-of-state verb)",
                w, sentence, "change_of_state", base,
            ))
            break

    base = 0.70 - _hedging_penalty(sentence)
    for w in REPETITION_WORDS:
        if re.search(rf"\b{w}\b", lower):
            matches.append(_AssumptionMatch(
                "Presupposition: implies prior occurrence (repetition/iteration)",
                w, sentence, "repetition", base,
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
                phrase, sentence, "epistemic_shortcut", base,
            ))
            break

    return matches


def _check_universal_quantifiers(sentence: str) -> list[_AssumptionMatch]:
    """Check for universal quantifiers implying blanket claims.
    Uses pattern-based 'None of X are Y' instead of bare 'none' keyword to reduce false positives.
    Suppresses meta-framing (e.g. 'presented as') where author clarifies scope, not asserting."""
    matches: list[_AssumptionMatch] = []
    words = _get_words_lower(sentence)
    lower = sentence.lower()

    base = 0.55 - _hedging_penalty(sentence)
    for w in UNIVERSAL_QUANTIFIERS:
        if w in words:
            matches.append(_AssumptionMatch(
                "Unstated universal claim: implies shared belief or blanket generalization",
                w, sentence, "universal", base,
            ))
            return matches

    # Pattern-based: "None of X are Y" - only when substantive (not meta-framing)
    if NONE_OF_X_PATTERN.search(sentence) and not META_FRAMING_SUPPRESS.search(sentence):
        base = 0.62 - _hedging_penalty(sentence)
        matches.append(_AssumptionMatch(
            "Unstated universal claim: universal negation over set (None of X are Y)",
            "none of X are Y", sentence, "universal", base,
        ))

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
                m.group(0)[:30], sentence, "vague_authority", base,
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
            m.group(1), sentence, "conclusion_marker", base,
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
                None, sentence, "loaded_question", base,
            ))
            return matches

    base = 0.75 - _hedging_penalty(sentence)
    if SUGGESTIVE_QUESTION_PATTERN.search(sentence):
        matches.append(_AssumptionMatch(
            "Suggestive question: stacked alternatives implying negative traits",
            None, sentence, "loaded_question", base,
        ))

    return matches


def _check_structural_assumptions(
    sentence: str,
    value_outcomes: list[str],
    necessity_modals: list[str],
) -> list[_AssumptionMatch]:
    """Check for structural patterns that imply unstated premises (Layer 2)."""
    matches: list[_AssumptionMatch] = []
    lower = sentence.lower()
    words = _get_words_lower(sentence)

    # Necessity modal + outcome: "X must adapt to survive" -> "Adaptation is necessary for survival"
    m = NECESSITY_MODAL_OUTCOME.search(sentence)
    if m:
        base = 0.72 - _hedging_penalty(sentence)
        matches.append(_AssumptionMatch(
            "Structural: Action is necessary for Outcome (necessity modal + outcome)",
            f"'{m.group(2)}' for '{m.group(3)}'",
            sentence,
            "necessity_modal_outcome",
            base,
        ))

    # Conditional necessity: "If X, we must Y"
    if CONDITIONAL_NECESSITY.search(sentence):
        base = 0.68 - _hedging_penalty(sentence)
        matches.append(_AssumptionMatch(
            "Structural: Condition implies necessity of consequence",
            "if/when ... must/need to/should",
            sentence,
            "necessity_modal_outcome",
            base,
        ))

    # Without X, Y: "Without reform, collapse is inevitable"
    m = WITHOUT_X_Y.search(sentence)
    if m:
        base = 0.70 - _hedging_penalty(sentence)
        matches.append(_AssumptionMatch(
            "Structural: X is necessary for avoiding Y",
            f"{m.group(1).strip()} -> {m.group(2)}",
            sentence,
            "without_x_y",
            base,
        ))

    # Value-loaded outcome: sentence has outcome term + necessity modal
    value_set = {v.lower() for v in value_outcomes}
    modal_phrases = ["must", "need to", "needs to", "require", "requires", "has to", "have to", "should"]
    has_modal = any(ph in lower for ph in modal_phrases)
    has_value_outcome = bool(words & value_set)
    if has_modal and has_value_outcome:
        # Avoid duplicate if we already matched necessity modal + outcome
        if not matches:
            base = 0.60 - _hedging_penalty(sentence)
            matches.append(_AssumptionMatch(
                "Structural: Outcome is desirable/necessary (value-loaded framing)",
                "value outcome + necessity modal",
                sentence,
                "value_loaded",
                base,
            ))

    # Causal claim: X leads to/results in/causes Y - causation assumed, not proven
    m = CAUSAL_LEADS_TO.search(sentence)
    if m:
        base = 0.58 - _hedging_penalty(sentence)
        matches.append(_AssumptionMatch(
            "Causal claim: X -> Y asserted; causation may be assumed rather than proven",
            f"{m.group(1).strip()} -> {m.group(2).strip()}",
            sentence,
            "causal",
            base,
        ))

    return matches


# Default value outcomes if lexicon missing
DEFAULT_VALUE_OUTCOMES = ["survival", "progress", "collapse", "excellence", "integrity", "stability", "innovation", "efficiency"]
DEFAULT_NECESSITY_MODALS = ["must", "need to", "needs to", "require", "requires", "has to", "have to", "should"]


class HiddenAssumptionExtractor:
    """
    Extracts hidden assumptions via rule-based pattern matching.
    Detects presuppositions, enthymemes, epistemic shortcuts, loaded questions,
    vague authority references, and structural patterns (necessity modals, conditionals).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4",
        lexicon_dir: Path | None = None,
    ) -> None:
        """
        Initialize the extractor.
        api_key and model are kept for API compatibility but ignored in rule-based mode.
        """
        self.api_key = api_key
        self.model = model
        if lexicon_dir is None:
            lexicon_dir = Path(__file__).parent.parent / "lexicons"
        self.lexicon_dir = Path(lexicon_dir)
        self._value_outcomes = _load_lexicon(self.lexicon_dir, "value_outcomes") or DEFAULT_VALUE_OUTCOMES
        self._necessity_modals = _load_lexicon(self.lexicon_dir, "necessity_modals") or DEFAULT_NECESSITY_MODALS

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
            all_matches.extend(
                _check_structural_assumptions(
                    sentence, self._value_outcomes, self._necessity_modals
                )
            )

        # Step 5: Expanded evidence/justification markers for context validation
        # Exclude "support" (ambiguous: "evidence supports" vs "why do you still support")

        def _has_justification_nearby(
            sent: str, sent_list: list[str], detection_type: str = ""
        ) -> bool:
            idx = next((i for i, s in enumerate(sent_list) if s == sent), -1)
            if idx < 0:
                return False
            # Check sentence + 2 before + 2 after (Step 5: local context)
            start = max(0, idx - 2)
            end = min(len(sent_list), idx + 3)
            context = " ".join(sent_list[start:end]).lower()
            # Phrase-based first (e.g. "evidence shows")
            for phrase in ("evidence shows", "evidence indicates", "evidence demonstrates"):
                if phrase in context:
                    return True
            words = set(re.findall(r"\b\w+\b", context))
            # For vague_authority, exclude "study/studies/shows" (often part of the pattern)
            base_words = frozenset({
                "because", "since", "data", "research", "supporting",
                "citation", "cited", "findings", "results", "empirical",
            })
            if detection_type != "vague_authority":
                base_words = base_words | {"study", "studies", "shows", "indicates", "demonstrates", "proves"}
            return bool(words & base_words)

        def _premises_provided_earlier(sent: str, sent_list: list[str]) -> bool:
            """Layer B: For conclusion markers, check if premises exist in earlier sentences."""
            idx = next((i for i, s in enumerate(sent_list) if s == sent), -1)
            if idx < 1:
                return False
            earlier = " ".join(sent_list[:idx]).lower()
            # Strong premise indicators: explicit reasoning, not vague "evidence" alone
            if "because" in earlier or "since" in earlier or "given that" in earlier:
                return True
            if "evidence shows" in earlier or "evidence indicates" in earlier or "data show" in earlier:
                return True
            premise_words = {"data", "study", "shows", "indicates", "demonstrates"}
            words = set(re.findall(r"\b\w+\b", earlier))
            return bool(words & premise_words)

        def _is_meta_language(sent: str) -> bool:
            """Step 7: Sentence reports/describes discourse rather than asserting."""
            lower = sent.lower()
            return any(rv in lower for rv in REPORTING_VERBS)

        from discourse_engine.scoring import (
            assumption_score,
            modal_strength_from_type,
            absence_of_support,
        )

        # Deduplicate; apply Layer B, calibrated scoring, meta-language, precision threshold
        seen: set[str] = set()
        result: list[AssumptionFlag] = []
        CONFIDENCE_FLOOR = 0.60  # Step 8: Precision > recall; only flag when confident

        for m in all_matches:
            full = f"{m.description} [trigger: '{m.trigger}']" if m.trigger else m.description
            if full not in seen:
                seen.add(full)
                # Layer B: enthymeme — if premises provided, suppress
                if m.detection_type == "conclusion_marker" and _premises_provided_earlier(m.sentence, sentences):
                    continue
                has_support = _has_justification_nearby(m.sentence, sentences, m.detection_type)
                # Step 4: Calibrated scoring
                modal = modal_strength_from_type(m.detection_type)
                causal = 0.7 if m.detection_type == "causal" else 0.3
                absent = absence_of_support(has_support)
                normative = 0.6 if (
                    "value" in m.description.lower()
                    or "necessity" in m.description.lower()
                    or "necessary" in m.description.lower()
                ) else 0.3
                conf = assumption_score(modal, causal, absent, normative)
                # Suppressions
                conf = _apply_suppressions(conf, m.sentence, _compute_density_factor(text))
                if _is_meta_language(m.sentence):
                    conf *= 0.5  # Step 7: meta-language
                conf = max(0.0, min(0.95, conf))
                if conf >= CONFIDENCE_FLOOR:
                    result.append(AssumptionFlag(description=full, sentence=m.sentence, confidence=conf))

        return result
