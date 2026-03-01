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
    """A detected logical fallacy with its pattern hint and source sentence."""

    name: str
    pattern_hint: str
    sentence: str


@dataclass
class AgendaFlag:
    """A detected hidden agenda technique with its pattern hint and source sentence."""

    family: str
    technique: str
    pattern_hint: str
    sentence: str


@dataclass
class AssumptionFlag:
    """A detected hidden assumption with its description and source sentence."""

    description: str
    sentence: str


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
