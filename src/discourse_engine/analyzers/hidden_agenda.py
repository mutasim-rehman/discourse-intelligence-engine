"""Rule-based hidden agenda detection (strategic discourse patterns)."""

import json
import re
from pathlib import Path

from discourse_engine.models.report import AgendaFlag


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
US_VS_THEM_PRONOUN_PATTERN = re.compile(
    r"\b(?:they|them|their)\s+(?:want|are|will|have|had)\s+",
    re.IGNORECASE,
)

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

    def analyze(self, text: str) -> list[AgendaFlag]:
        """Return list of AgendaFlag for detected agenda techniques."""
        if not text or not text.strip():
            return []

        flags: list[AgendaFlag] = []
        lower = text.lower()

        # Deflecting
        for pat in WHATABOUTISM_PATTERNS:
            if pat.search(text):
                flags.append(AgendaFlag(
                    family="Deflecting",
                    technique="Whataboutism",
                    pattern_hint="counter-accusation or deflection ('what about', 'how about')",
                ))
                break

        for pat in SHIFTING_GOALPOST_PATTERNS:
            if pat.search(text):
                flags.append(AgendaFlag(
                    family="Deflecting",
                    technique="Shifting Goalpost",
                    pattern_hint="relativizing by redefining ('this is not X, it's Y')",
                ))
                break

        for pat in SIDE_NOTE_PATTERNS:
            if pat.search(text):
                flags.append(AgendaFlag(
                    family="Deflecting",
                    technique="Side Note",
                    pattern_hint="diversion or tangential insertion ('Meanwhile', 'In other news')",
                ))
                break

        # Dividing
        if US_VS_THEM_PRONOUN_PATTERN.search(text):
            flags.append(AgendaFlag(
                family="Dividing",
                technique="Us vs Them",
                pattern_hint="pronoun polarization ('they want', 'they are')",
            ))

        for w in US_VS_THEM_HOSTILE:
            if w in lower:
                flags.append(AgendaFlag(
                    family="Dividing",
                    technique="Us vs Them",
                    pattern_hint="dehumanizing or hostile out-group language",
                ))
                break

        for pat in GATEKEEPING_PATTERNS:
            if pat.search(text):
                flags.append(AgendaFlag(
                    family="Dividing",
                    technique="Gatekeeping",
                    pattern_hint="defining who 'truly' belongs ('only real', 'true patriots')",
                ))
                break

        # Asserting
        for pat in SPECULATION_PATTERNS:
            if pat.search(text):
                flags.append(AgendaFlag(
                    family="Asserting",
                    technique="Speculation",
                    pattern_hint="speculative or unconfirmed framing ('rumors', 'allegedly')",
                ))
                break

        for pat in VAGUENESS_AGENDA_PATTERNS:
            if pat.search(text):
                flags.append(AgendaFlag(
                    family="Asserting",
                    technique="Vagueness",
                    pattern_hint="vague authority without specification",
                ))
                break

        # Personalizing
        for pat in MUD_HONEY_PATTERNS:
            if pat.search(text):
                flags.append(AgendaFlag(
                    family="Personalizing",
                    technique="Mud & Honey",
                    pattern_hint="personal attack or derogatory framing",
                ))
                break

        # Framing (emotional sensationalism)
        fear_lower = [t.lower() for t in self._fear_terms]
        if any(t in lower for t in fear_lower):
            flags.append(AgendaFlag(
                family="Framing",
                technique="Emotional Sensationalism",
                pattern_hint="fear or threat language",
            ))

        # Deduplicate by (family, technique)
        seen: set[tuple[str, str]] = set()
        deduped: list[AgendaFlag] = []
        for f in flags:
            key = (f.family, f.technique)
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        return deduped
