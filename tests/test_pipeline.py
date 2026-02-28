"""Tests for the Discourse Intelligence Engine pipeline."""

import pytest

from discourse_engine import run_pipeline, format_report


SAMPLE_TEXT = """
Either we pass this law, or our nation will collapse.
We must protect our people from this growing threat.
They want to destroy everything we stand for.
""".strip()


def test_run_pipeline_returns_report() -> None:
    """Pipeline returns a Report with expected structure."""
    report = run_pipeline(SAMPLE_TEXT)
    assert report.word_count == 27
    assert report.sentence_count == 3
    assert report.trigger_profile is not None
    assert report.tone is not None
    assert report.modal_verbs_detected is not None
    assert report.pronoun_framing is not None
    assert report.logical_fallacy_flags is not None
    assert report.hidden_assumptions is not None


def test_trigger_profile_levels() -> None:
    """Trigger profile has Low/Moderate/High levels."""
    report = run_pipeline(SAMPLE_TEXT)
    for level in [
        report.trigger_profile.fear_level,
        report.trigger_profile.authority_level,
        report.trigger_profile.identity_level,
    ]:
        assert level in ("Low", "Moderate", "High")


def test_modal_verbs_detected() -> None:
    """Modal verb 'must' is detected."""
    report = run_pipeline(SAMPLE_TEXT)
    assert "must" in report.modal_verbs_detected


def test_pronoun_framing() -> None:
    """Pronouns we/they are counted."""
    report = run_pipeline(SAMPLE_TEXT)
    assert report.pronoun_framing.get("we", 0) >= 1
    assert report.pronoun_framing.get("they", 0) >= 1
    assert report.pronoun_insight is not None
    assert "in-group" in report.pronoun_insight.lower() or "out-group" in report.pronoun_insight.lower()


def test_logical_fallacy_flags() -> None:
    """False Dilemma and Appeal to Fear are flagged."""
    report = run_pipeline(SAMPLE_TEXT)
    fallacy_names = [f.name for f in report.logical_fallacy_flags]
    assert "False Dilemma" in fallacy_names
    assert "Appeal to Fear" in fallacy_names


def test_false_dilemma_vs_genuine_dichotomy() -> None:
    """False dilemma is flagged only when options are not exhaustive (X vs Y, not X vs not-X)."""
    # Genuine dichotomy: X vs not-X — should NOT be flagged
    report_dichotomy = run_pipeline("Either the file exists or it doesn't.")
    fallacy_names_dichotomy = [f.name for f in report_dichotomy.logical_fallacy_flags]
    assert "False Dilemma" not in fallacy_names_dichotomy

    # False dilemma: X vs Y (non-exhaustive) — should be flagged
    report_false = run_pipeline("Either you support this bill or you hate this country.")
    fallacy_names_false = [f.name for f in report_false.logical_fallacy_flags]
    assert "False Dilemma" in fallacy_names_false


def test_format_report_produces_expected_sections() -> None:
    """Formatted report contains all expected sections."""
    report = run_pipeline(SAMPLE_TEXT)
    formatted = format_report(report)
    assert "--- Discourse Analysis Report ---" in formatted
    assert "Word Count:" in formatted
    assert "Sentence Count:" in formatted
    assert "Trigger Profile:" in formatted
    assert "Modal Verbs Detected:" in formatted
    assert "Pronoun Framing:" in formatted
    assert "Logical Fallacy Flags:" in formatted
    assert "Hidden Assumptions:" in formatted
    assert "Tone:" in formatted


def test_empty_text() -> None:
    """Empty text produces valid report with zeros."""
    report = run_pipeline("")
    assert report.word_count == 0
    assert report.sentence_count == 0
    assert report.tone == []
    assert report.modal_verbs_detected == []
    assert report.pronoun_framing == {}
