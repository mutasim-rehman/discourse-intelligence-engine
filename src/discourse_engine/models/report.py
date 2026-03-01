"""Structured report and supporting data models."""

from dataclasses import dataclass


@dataclass
class TriggerProfile:
    """Levels of fear, authority, and identity framing in text."""

    fear_level: str  # Low | Moderate | High
    authority_level: str
    identity_level: str


@dataclass
class FallacyFlag:
    """A detected logical fallacy with pattern hint, source sentence, and confidence."""

    name: str
    pattern_hint: str
    sentence: str
    confidence: float = 0.0  # 0-1, how sure we are this is a genuine instance


@dataclass
class AgendaFlag:
    """A detected hidden agenda technique with pattern hint, source sentence, and confidence."""

    family: str
    technique: str
    pattern_hint: str
    sentence: str
    confidence: float = 0.0  # 0-1


@dataclass
class AssumptionFlag:
    """A detected hidden assumption with description, source sentence, and confidence."""

    description: str
    sentence: str
    confidence: float = 0.0  # 0-1


@dataclass
class Report:
    """Structured analysis report output."""

    word_count: int
    sentence_count: int
    trigger_profile: TriggerProfile
    tone: list[str]
    modal_verbs_detected: list[str]
    pronoun_framing: dict[str, int]
    pronoun_insight: str | None
    logical_fallacy_flags: list[FallacyFlag]
    hidden_assumptions: list[AssumptionFlag]
    hidden_agenda_flags: list[AgendaFlag]
    context_note: str | None = None
    satire_probability: float = 0.0
    content_type_hint: str = "Genuine Argument"
