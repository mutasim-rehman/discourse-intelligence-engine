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
    """A detected logical fallacy with its pattern hint."""

    name: str
    pattern_hint: str


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
    hidden_assumptions: list[str]
