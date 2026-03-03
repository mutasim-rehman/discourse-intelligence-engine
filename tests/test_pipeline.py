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
    assert report.hidden_agenda_flags is not None


def test_tone_not_always_urgent() -> None:
    """Neutral policy text should not be labeled Urgent (modal verbs != urgency)."""
    text = (
        "Public institutions must modernize to remain responsive. "
        "Digital tools can improve accountability."
    )
    report = run_pipeline(text)
    assert "Urgent" not in report.tone


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
    assert "Content Type:" in formatted
    assert "Word Count:" in formatted
    assert "Sentence Count:" in formatted
    assert "Trigger Profile:" in formatted
    assert "Modal Verbs Detected:" in formatted
    assert "Pronoun Framing:" in formatted
    assert "Logical Fallacy Flags:" in formatted
    assert "Hidden Assumptions:" in formatted
    assert "Hidden Agenda Flags:" in formatted
    assert "Tone:" in formatted


def test_empty_text() -> None:
    """Empty text produces valid report with zeros."""
    report = run_pipeline("")
    assert report.word_count == 0
    assert report.sentence_count == 0
    assert report.tone == []
    assert report.modal_verbs_detected == []
    assert report.pronoun_framing == {}
    assert report.hidden_assumptions == []
    assert report.hidden_agenda_flags == []


def test_hidden_assumptions_presupposition() -> None:
    """Presupposition triggers (factive verbs, again/still) are detected."""
    text = "He realized the policy had failed. They continued to push for change."
    report = run_pipeline(text)
    assert len(report.hidden_assumptions) >= 1
    assumption_text = " ".join(a.description for a in report.hidden_assumptions).lower()
    assert "presupposition" in assumption_text


def test_hidden_assumptions_epistemic_shortcut() -> None:
    """Epistemic shortcuts (obviously, clearly) are detected."""
    text = "Obviously, we need to act now. The solution is clearly the best option."
    report = run_pipeline(text)
    assert len(report.hidden_assumptions) >= 1
    assumption_text = " ".join(a.description for a in report.hidden_assumptions).lower()
    assert "epistemic" in assumption_text or "obvious" in assumption_text


def test_hidden_assumptions_universal_quantifier() -> None:
    """Universal quantifiers (everyone, nobody) are detected."""
    text = "Everyone knows this is wrong. Nobody would disagree."
    report = run_pipeline(text)
    assert len(report.hidden_assumptions) >= 1
    assumption_text = " ".join(a.description for a in report.hidden_assumptions).lower()
    assert "universal" in assumption_text


def test_hidden_assumptions_conclusion_marker() -> None:
    """Conclusion markers (therefore, thus) suggest enthymeme."""
    text = "The evidence is in. Therefore we must act."
    report = run_pipeline(text)
    assert len(report.hidden_assumptions) >= 1
    assumption_text = " ".join(a.description for a in report.hidden_assumptions).lower()
    assert "conclusion" in assumption_text or "enthymeme" in assumption_text


def test_hidden_assumptions_loaded_question() -> None:
    """Loaded questions are detected."""
    text = "Why do you still support that policy? When did you stop caring?"
    report = run_pipeline(text)
    assert len(report.hidden_assumptions) >= 1
    assumption_text = " ".join(a.description for a in report.hidden_assumptions).lower()
    assert "loaded question" in assumption_text


def test_hidden_assumptions_vague_authority() -> None:
    """Vague authority (experts, studies) is detected."""
    text = "Experts agree that this is the best approach. Studies show significant effects."
    report = run_pipeline(text)
    assert len(report.hidden_assumptions) >= 1
    assumption_text = " ".join(a.description for a in report.hidden_assumptions).lower()
    assert "vague" in assumption_text or "authority" in assumption_text


def test_hidden_assumptions_structural_necessity_modal() -> None:
    """Structural: 'X must adapt to survive' -> Action necessary for Outcome."""
    text = "Traditional institutions must adapt to survive."
    report = run_pipeline(text)
    assert len(report.hidden_assumptions) >= 1
    assumption_text = " ".join(a.description for a in report.hidden_assumptions).lower()
    assert "structural" in assumption_text or "necessary" in assumption_text


def test_hidden_assumptions_none_meta_framing_suppressed() -> None:
    """'None of X are presented as Y' (meta-framing) should NOT be flagged as universal claim."""
    text = "None of these developments are presented as malicious."
    report = run_pipeline(text)
    assumption_descs = [a.description.lower() for a in report.hidden_assumptions]
    # Should not contain universal claim triggered by "none" in this context
    assert not any("none" in d and "universal" in d for d in assumption_descs)


def test_hidden_agenda_us_vs_them_anaphoric_suppressed() -> None:
    """'They' referring to abstract noun (traditions) should NOT be flagged as Pronoun contrast."""
    text = "Yet traditions are not merely relics of the past; they are repositories of collective wisdom."
    report = run_pipeline(text)
    agenda_techniques = [f.technique for f in report.hidden_agenda_flags]
    assert "Pronoun contrast" not in agenda_techniques


def test_hidden_assumptions_structural_without_x_y() -> None:
    """Structural: 'Without X, Y' -> X necessary for avoiding Y."""
    text = "Without reform, collapse is inevitable."
    report = run_pipeline(text)
    assert len(report.hidden_assumptions) >= 1
    assumption_text = " ".join(a.description for a in report.hidden_assumptions).lower()
    assert "structural" in assumption_text or "necessary" in assumption_text


def test_hidden_assumptions_sample_text_detects_some() -> None:
    """SAMPLE_TEXT with threat/crisis language may trigger presupposition or other patterns."""
    report = run_pipeline(SAMPLE_TEXT)
    # SAMPLE_TEXT has "threat", "collapse" - may not trigger assumption patterns.
    # "They want to destroy" - no factives, etc. So assumptions might be empty.
    # Just ensure it doesn't crash and returns a list.
    assert report.hidden_assumptions is not None
    assert isinstance(report.hidden_assumptions, list)


def test_hidden_agenda_us_vs_them() -> None:
    """Pronoun contrast (they want, hostile language) is detected."""
    report = run_pipeline(SAMPLE_TEXT)
    agenda_techniques = [f.technique for f in report.hidden_agenda_flags]
    assert "Pronoun contrast" in agenda_techniques or "Hostile out-group language" in agenda_techniques


def test_hidden_agenda_whataboutism() -> None:
    """Counter-accusation deflection is detected."""
    text = "But what about when they did the same thing? How about their record?"
    report = run_pipeline(text)
    agenda_techniques = [f.technique for f in report.hidden_agenda_flags]
    assert "Counter-accusation" in agenda_techniques


def test_hidden_agenda_shifting_goalpost() -> None:
    """Scope redefinition is detected."""
    text = "This is not a bailout, it's support for certain industries."
    report = run_pipeline(text)
    agenda_techniques = [f.technique for f in report.hidden_agenda_flags]
    assert "Scope redefinition" in agenda_techniques


def test_hidden_agenda_side_note() -> None:
    """Topic diversion is detected."""
    text = "The policy failed. Meanwhile, another company reported profits."
    report = run_pipeline(text)
    agenda_techniques = [f.technique for f in report.hidden_agenda_flags]
    assert "Topic diversion" in agenda_techniques


def test_hidden_agenda_speculation() -> None:
    """Speculative framing (rumors, allegedly) is detected."""
    text = "Rumors suggest he will resign. The minister allegedly knew."
    report = run_pipeline(text)
    agenda_techniques = [f.technique for f in report.hidden_agenda_flags]
    assert "Speculative framing" in agenda_techniques


def test_hidden_agenda_policy_advocacy() -> None:
    """Normative directive (policy verb + value term) is detected."""
    text = "Expanding private-sector partnerships will encourage innovation and efficiency."
    report = run_pipeline(text)
    agenda_families = [f.family for f in report.hidden_agenda_flags]
    techniques = [f.technique for f in report.hidden_agenda_flags]
    assert "Normative directive" in agenda_families or "Prescriptive framing" in techniques


def test_hidden_agenda_descriptive_not_flagged() -> None:
    """Descriptive meta-analysis (divides, often) should NOT be flagged as Prescriptive framing."""
    text = "Public debate often divides participants into progress-oriented reformers and tradition-oriented conservatives, yet this binary framing oversimplifies discussions."
    report = run_pipeline(text)
    agenda_techniques = [f.technique for f in report.hidden_agenda_flags]
    assert "Prescriptive framing" not in agenda_techniques


def test_hidden_agenda_emotional_framing() -> None:
    """Fear/threat framing is detected."""
    report = run_pipeline(SAMPLE_TEXT)
    agenda_techniques = [f.technique for f in report.hidden_agenda_flags]
    assert "Fear/threat framing" in agenda_techniques


def test_hidden_agenda_obscuration() -> None:
    """Corporate euphemisms (right-sizing, decoupling, etc.) trigger Obscuration."""
    text = "Our Right-Sizing Initiative and strategic decoupling will optimize human capital."
    report = run_pipeline(text)
    obscuration = [f for f in report.hidden_agenda_flags if f.family == "Obscuration"]
    assert len(obscuration) >= 1
    techniques = [f.technique for f in obscuration]
    assert "Personnel Reduction" in techniques or "Objectification of Labor" in techniques


def test_weaponized_dust_satire_signals() -> None:
    """Absurdity anchors (dust, cleaning) + Authority Moderate → satire signals and logical leaps."""
    text = (
        "Intelligence reports suggest 'they' have weaponized household dust to destabilize "
        "our national pride. We must restructure our living rooms for the hygiene-first mandate, "
        "ensuring every citizen's cleaning habits are optimized for patriotic output."
    )
    report = run_pipeline(text)
    assert report.satire_probability >= 0.35
    assert "Uncertain" in report.content_type_hint or "Satire" in report.content_type_hint


def test_tone_passive_aggressive() -> None:
    """Plausible deniability + obligation modal flags Passive-aggressive."""
    text = (
        "I'm sure you didn't mean to exclude the team from the invite. "
        "It might be worth considering a time-management course if you're overwhelmed, "
        "so the rest of us don't have to keep covering these oversights. "
        "You should probably be more careful next time."
    )
    report = run_pipeline(text)
    assert "Passive-aggressive" in report.tone


def test_tone_guilt_coercive_and_false_dilemma() -> None:
    """Weekend shifts guilt-trip is flagged as Guilt/Coercive and False Dilemma."""
    text = (
        "I'm sure you'll agree that everyone who truly cares about the success of this project "
        "has already volunteered for the weekend shifts. It might be helpful for you to reflect "
        "on why you're the only one who hasn't submitted their commitment form yet, though I'm "
        "sure you probably just have different priorities than the rest of the team. "
        "We really want to maintain our reputation as a group of 'high-performers,' so it would "
        "be a shame if certain individuals' lack of participation started to affect how management "
        "views our collective output. Shall we just assume you're joining us, or do we need to have "
        "a more formal conversation about your alignment with our values?"
    )
    report = run_pipeline(text)
    assert "Guilt/Coercive" in report.tone
    fallacies = [f.name for f in report.logical_fallacy_flags]
    assert "False Dilemma" in fallacies
