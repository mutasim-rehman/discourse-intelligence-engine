"""Rule-based hidden agenda detection (strategic discourse patterns)."""

import json
import re
from pathlib import Path

from discourse_engine.models.report import AgendaFlag
from discourse_engine.utils.text_utils import (
    sentence_containing_offset,
    split_sentences,
    split_sentences_with_offsets,
)


def _load_lexicon(lexicon_dir: Path, name: str) -> list[str]:
    """Load a JSON lexicon file."""
    path = lexicon_dir / f"{name}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


# ---------------------------------------------------------------------------
# Deflecting: deflect discussion, relativize, steer elsewhere
# ---------------------------------------------------------------------------

# Whataboutism: counter-accusation instead of addressing the argument
WHATABOUTISM_PATTERNS = (
    re.compile(r"\b(?:but\s+)?what\s+about\b", re.IGNORECASE),
    re.compile(r"\bhow\s+about\s+when\b", re.IGNORECASE),
    re.compile(r"\byet\s+(?:what\s+about|how\s+about)\b", re.IGNORECASE),
)

# Shifting goalpost: "This is not X, this is Y"
SHIFTING_GOALPOST_PATTERNS = (
    re.compile(r"\bthis\s+is\s+not\s+(?:\w+\s+)?(?:,\s*)?(?:it['\u2019]?s\s+)?(?:a\s+)?\w+", re.IGNORECASE),
    re.compile(r"\bthat['\u2019]?s\s+not\s+\w+[,.]\s*(?:it['\u2019]?s|that['\u2019]?s)\s+", re.IGNORECASE),
)

# Side note / diversion: "Meanwhile" introducing unrelated or tangentially related content
SIDE_NOTE_PATTERNS = (
    re.compile(r"^\s*meanwhile[,.]\s+", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\bmeanwhile[,.]\s+\w+", re.IGNORECASE),
    re.compile(r"\bin\s+other\s+news[,.]\s+", re.IGNORECASE),
)

# ---------------------------------------------------------------------------
# Dividing: sow division, us vs them
# ---------------------------------------------------------------------------

# Us vs them: pronoun polarization (they/them vs we/us) with negative framing
# Requires we/they CONTRAST in same sentence - not every "they" is polarization.
# Excludes anaphoric "they" referring to abstract nouns (traditions, reforms, etc.)
US_VS_THEM_PRONOUN_PATTERN = re.compile(
    r"\b(?:they|them|their)\s+(?:want|are|will|have|had)\s+",
    re.IGNORECASE,
)
IN_GROUP_PRONOUNS = frozenset({"we", "us", "our"})
ABSTRACT_ANAPHOR_NOUNS = frozenset({
    "traditions", "reforms", "policies", "developments", "institutions",
    "changes", "systems", "ideas", "values", "norms", "practices",
    "concepts", "principles", "standards", "procedures",
})

# Dehumanizing or poisoning language
US_VS_THEM_HOSTILE = frozenset({
    "poisoning", "enemy", "enemies", "invaders", "infest",
})

# Gatekeeping: "real", "true", "only genuine", "the only real"
GATEKEEPING_PATTERNS = (
    re.compile(r"\b(?:the\s+)?only\s+real\s+\w+", re.IGNORECASE),
    re.compile(r"\btrue\s+(?:believers?|patriots?|americans?)\b", re.IGNORECASE),
    re.compile(r"\bgenuine\s+\w+\b", re.IGNORECASE),
)

# ---------------------------------------------------------------------------
# Asserting: claim without evidence, speculation, vagueness
# ---------------------------------------------------------------------------

# Speculation: rumors, allegedly, reportedly, might/could (speculative)
SPECULATION_PATTERNS = (
    re.compile(r"\brumors?\b", re.IGNORECASE),
    re.compile(r"\ballegedly\b", re.IGNORECASE),
    re.compile(r"\breportedly\b", re.IGNORECASE),
    re.compile(r"\bit\s+(?:has\s+)?been\s+(?:widely\s+)?(?:reported|rumored)\b", re.IGNORECASE),
)

# Vagueness: experts, studies, many (reuse from assumptions - agenda angle)
VAGUENESS_AGENDA_PATTERNS = (
    re.compile(r"\bexperts?\s+(?:say|agree|believe|warn)", re.IGNORECASE),
    re.compile(r"\bstudies?\s+(?:show|suggest|indicate)", re.IGNORECASE),
    re.compile(r"\bmany\s+(?:people|critics|observers)\s+", re.IGNORECASE),
)

# ---------------------------------------------------------------------------
# Personalizing: ad hominem, mud-slinging (agenda angle)
# ---------------------------------------------------------------------------

# Personal attack / mud-slinging: derogatory nicknames, character attacks
MUD_HONEY_PATTERNS = (
    re.compile(r"\b(?:hypocrite|liar|crook|fraud)\b", re.IGNORECASE),
    re.compile(r"\b(?:bedraggled|terrifying)\s+\w+\b", re.IGNORECASE),
)

# ---------------------------------------------------------------------------
# Framing: emotional sensationalism (loaded language)
# ---------------------------------------------------------------------------

# Fallback if lexicon missing
DEFAULT_FEAR_TERMS = frozenset({
    "collapse", "destroy", "threat", "danger", "catastrophe", "crisis",
    "terror", "disaster", "attack",
})

# ---------------------------------------------------------------------------
# Advocating: policy advocacy, rhetorical flow (Layer 2)
# ---------------------------------------------------------------------------

# Problem markers: risk, failure, crisis, without X, fails to
PROBLEM_PATTERNS = (
    re.compile(r"\b(?:risk|risks|fails?\s+to|failure|failing)\b", re.IGNORECASE),
    re.compile(r"\bwithout\s+\w+", re.IGNORECASE),
    re.compile(r"\b(?:disconnect|disconnected|stagnat|inevitable)\b", re.IGNORECASE),
)

# Justification markers: because, in order to, allows, enables
JUSTIFICATION_PATTERNS = (
    re.compile(r"\bbecause\b", re.IGNORECASE),
    re.compile(r"\bin\s+order\s+to\b", re.IGNORECASE),
    re.compile(r"\b(?:allows|enables|will\s+encourage|can\s+restructure)\b", re.IGNORECASE),
)

DEFAULT_POLICY_VERBS = [
    "expand", "restructure", "eliminate", "adopt", "reform", "privatize",
    "deregulate", "subsidize", "mandate", "incentivize",
]
DEFAULT_VALUE_TERMS = [
    "innovation", "efficiency", "stability", "integrity", "freedom", "progress", "reform",
]

# ---------------------------------------------------------------------------
# Obscuration: corporate euphemisms that mask real-world actions (high confidence)
# ---------------------------------------------------------------------------
OBSCURATION_PATTERNS = (
    (re.compile(r"\b(?:right-sizing|decoupling|headcount\s+harmonization)\b", re.IGNORECASE),
     "Personnel Reduction", "Layoffs / Firing", 0.88),
    (re.compile(r"\b(?:human\s+capital|talent-pool\s+resources?)\b", re.IGNORECASE),
     "Objectification of Labor", "Dehumanization", 0.85),
    (re.compile(r"\b(?:bandwidth|availability|synergy)\b", re.IGNORECASE),
     "Workload Escalation", "Exploitation / Overwork", 0.82),
    (re.compile(r"\btransitioned\s+to\s+the\s+marketplace\b", re.IGNORECASE),
     "Euphemistic Termination", "Firing", 0.90),
)


class HiddenAgendaAnalyzer:
    """
    Detects hidden agendas via rule-based pattern matching.
    Identifies Deflecting, Dividing, Asserting, Personalizing, and Framing techniques.
    """

    def __init__(self, lexicon_dir: Path | None = None) -> None:
        if lexicon_dir is None:
            lexicon_dir = Path(__file__).parent.parent / "lexicons"
        self.lexicon_dir = Path(lexicon_dir)
        self._fear_terms = _load_lexicon(self.lexicon_dir, "fear_terms") or list(DEFAULT_FEAR_TERMS)
        self._policy_verbs = _load_lexicon(self.lexicon_dir, "policy_advocacy_verbs") or DEFAULT_POLICY_VERBS
        self._value_terms = _load_lexicon(self.lexicon_dir, "value_terms") or DEFAULT_VALUE_TERMS

    def analyze(self, text: str) -> list[AgendaFlag]:
        """Return list of AgendaFlag for detected agenda techniques."""
        if not text or not text.strip():
            return []

        flags: list[AgendaFlag] = []
        lower = text.lower()
        sentences_with_offsets = split_sentences_with_offsets(text)

        def _sentence_at(match: re.Match) -> str:
            return sentence_containing_offset(sentences_with_offsets, match.start())

        def _sentence_for_term(term: str) -> str:
            m = re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE)
            return _sentence_at(m) if m else (sentences_with_offsets[0][0] if sentences_with_offsets else "")

        # Topic deflection (neutral terminology)
        for pat in WHATABOUTISM_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append(AgendaFlag(
                    family="Topic deflection",
                    technique="Counter-accusation",
                    pattern_hint="counter-accusation or deflection ('what about', 'how about')",
                    sentence=_sentence_at(m),
                    confidence=0.82,
                ))
                break

        for pat in SHIFTING_GOALPOST_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append(AgendaFlag(
                    family="Topic deflection",
                    technique="Scope redefinition",
                    pattern_hint="relativizing by redefining ('this is not X, it's Y')",
                    sentence=_sentence_at(m),
                    confidence=0.75,
                ))
                break

        for pat in SIDE_NOTE_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append(AgendaFlag(
                    family="Topic deflection",
                    technique="Topic diversion",
                    pattern_hint="diversion or tangential insertion ('Meanwhile', 'In other news')",
                    sentence=_sentence_at(m),
                    confidence=0.72,
                ))
                break

        # In-group/out-group framing (neutral terminology)
        m = US_VS_THEM_PRONOUN_PATTERN.search(text)
        if m:
            sent = _sentence_at(m)
            sent_lower = sent.lower()
            sent_words = set(re.findall(r"\b\w+\b", sent_lower))
            has_in_group = bool(sent_words & IN_GROUP_PRONOUNS)
            if has_in_group:
                flags.append(AgendaFlag(
                    family="In-group/out-group framing",
                    technique="Pronoun contrast",
                    pattern_hint="pronoun polarization ('they want', 'they are') with we/us contrast",
                    sentence=sent,
                    confidence=0.72,
                ))

        for w in US_VS_THEM_HOSTILE:
            if w in lower:
                flags.append(AgendaFlag(
                    family="In-group/out-group framing",
                    technique="Hostile out-group language",
                    pattern_hint="dehumanizing or hostile out-group language",
                    sentence=_sentence_for_term(w),
                    confidence=0.78,
                ))
                break

        for pat in GATEKEEPING_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append(AgendaFlag(
                    family="In-group/out-group framing",
                    technique="Boundary definition",
                    pattern_hint="defining who 'truly' belongs ('only real', 'true patriots')",
                    sentence=_sentence_at(m),
                    confidence=0.70,
                ))
                break

        # Unsupported claim
        for pat in SPECULATION_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append(AgendaFlag(
                    family="Unsupported claim",
                    technique="Speculative framing",
                    pattern_hint="speculative or unconfirmed framing ('rumors', 'allegedly')",
                    sentence=_sentence_at(m),
                    confidence=0.80,
                ))
                break

        for pat in VAGUENESS_AGENDA_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append(AgendaFlag(
                    family="Unsupported claim",
                    technique="Vague authority",
                    pattern_hint="vague authority without specification",
                    sentence=_sentence_at(m),
                    confidence=0.68,
                ))
                break

        # Personal attack
        for pat in MUD_HONEY_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append(AgendaFlag(
                    family="Personal attack",
                    technique="Derogatory framing",
                    pattern_hint="personal attack or derogatory framing",
                    sentence=_sentence_at(m),
                    confidence=0.74,
                ))
                break

        # Emotional intensity
        fear_lower = [t.lower() for t in self._fear_terms]
        for t in fear_lower:
            if t in lower:
                flags.append(AgendaFlag(
                    family="Emotional intensity",
                    technique="Fear/threat framing",
                    pattern_hint="fear or threat language",
                    sentence=_sentence_for_term(t),
                    confidence=0.62,
                ))
                break

        # Obscuration: corporate euphemisms (high hidden-agenda confidence)
        for pat, technique, real_action, conf in OBSCURATION_PATTERNS:
            m = pat.search(text)
            if m:
                flags.append(AgendaFlag(
                    family="Obscuration",
                    technique=technique,
                    pattern_hint=f"obscuring jargon: likely {real_action}",
                    sentence=_sentence_at(m),
                    confidence=conf,
                ))

        # Advocating (Layer 2): policy advocacy verbs + value terms
        sentences = split_sentences(text)
        policy_set = {v.lower() for v in self._policy_verbs}
        value_set = {v.lower() for v in self._value_terms}

        def _has_policy_verb(s: str) -> bool:
            s_lower = s.lower()
            return any(pv in s_lower for pv in policy_set)

        def _has_value_term(s: str) -> bool:
            words = set(re.findall(r"\b\w+\b", s.lower()))
            return bool(words & value_set)

        # Prescriptive: should, must, need to, recommend, requires — advocating action
        # Descriptive: divides, characterizes, describes, often — meta-analysis of discourse
        PRESCRIPTIVE_MARKERS = re.compile(
            r"\b(?:should|must|need\s+to|requires?|recommend|prioritize|ensure|will\s+encourage|encourage)\b",
            re.IGNORECASE,
        )
        DESCRIPTIVE_MARKERS = re.compile(
            r"\b(?:divides?|characterizes?|describes?|often|typically|frequently|tends?\s+to)\b",
            re.IGNORECASE,
        )

        for sent in sentences:
            has_policy = _has_policy_verb(sent)
            has_value = _has_value_term(sent)
            is_prescriptive = bool(PRESCRIPTIVE_MARKERS.search(sent))
            is_descriptive = bool(DESCRIPTIVE_MARKERS.search(sent))
            # Only flag when prescriptive; suppress when descriptive meta-analysis
            if has_policy and has_value and is_prescriptive and not is_descriptive:
                flags.append(AgendaFlag(
                    family="Normative directive",
                    technique="Prescriptive framing",
                    pattern_hint="policy advocacy verb + value term (prescriptive)",
                    sentence=sent,
                    confidence=0.72,
                ))
                break

        # Normative directive: rhetorical flow Problem -> Solution -> Justification
        problem_idxs: list[int] = []
        solution_idxs: list[int] = []
        justification_idxs: list[int] = []

        for i, sent in enumerate(sentences):
            if any(pat.search(sent) for pat in PROBLEM_PATTERNS):
                problem_idxs.append(i)
            if _has_policy_verb(sent):
                solution_idxs.append(i)
            if any(pat.search(sent) for pat in JUSTIFICATION_PATTERNS):
                justification_idxs.append(i)

        # Triadic structure: problem before solution before justification (within 2-sentence gap)
        for pi in problem_idxs:
            for si in solution_idxs:
                if si > pi and si - pi <= 2:
                    for ji in justification_idxs:
                        if ji > si and ji - si <= 2:
                            flags.append(AgendaFlag(
                                family="Normative directive",
                                technique="Problem-solution structure",
                                pattern_hint="triadic structure: problem -> solution -> justification",
                                sentence=sentences[si],
                                confidence=0.68,
                            ))
                            break
                    else:
                        continue
                    break
            else:
                continue
            break

        # Deduplicate by (family, technique)
        seen: set[tuple[str, str]] = set()
        deduped: list[AgendaFlag] = []
        for f in flags:
            key = (f.family, f.technique)
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        return deduped
