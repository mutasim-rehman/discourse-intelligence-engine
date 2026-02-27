"""Modular analyzers for discourse analysis pipeline."""

from discourse_engine.analyzers.base import Analyzer
from discourse_engine.analyzers.statistics import StatisticsAnalyzer
from discourse_engine.analyzers.trigger_profile import TriggerProfileAnalyzer
from discourse_engine.analyzers.tone import ToneAnalyzer
from discourse_engine.analyzers.modal_pronoun import ModalPronounAnalyzer
from discourse_engine.analyzers.logical_fallacy import LogicalFallacyAnalyzer
from discourse_engine.analyzers.hidden_assumptions import HiddenAssumptionExtractor

__all__ = [
    "Analyzer",
    "StatisticsAnalyzer",
    "TriggerProfileAnalyzer",
    "ToneAnalyzer",
    "ModalPronounAnalyzer",
    "LogicalFallacyAnalyzer",
    "HiddenAssumptionExtractor",
]
