"""Discourse Intelligence Engine - NLP-driven analysis of structural logic in language."""

from discourse_engine.main import run_pipeline, format_report
from discourse_engine.models.report import Report
from discourse_engine.v4.dialogue_pipeline import (
    parse_speaker_tagged_text,
    run_dialogue_analysis,
    dialogue_report_to_dict,
    format_dialogue_report,
)
from discourse_engine.v4.models import DialogueReport

__all__ = [
    "run_pipeline",
    "format_report",
    "Report",
    # v4 dialogue API
    "run_dialogue_analysis",
    "parse_speaker_tagged_text",
    "dialogue_report_to_dict",
    "format_dialogue_report",
    "DialogueReport",
]
