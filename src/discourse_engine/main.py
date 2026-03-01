"""Pipeline entry point and report formatting."""

import re

from discourse_engine.analyzers.statistics import StatisticsAnalyzer
from discourse_engine.analyzers.trigger_profile import TriggerProfileAnalyzer
from discourse_engine.analyzers.tone import ToneAnalyzer
from discourse_engine.analyzers.modal_pronoun import ModalPronounAnalyzer
from discourse_engine.analyzers.logical_fallacy import LogicalFallacyAnalyzer
from discourse_engine.analyzers.hidden_assumptions import HiddenAssumptionExtractor
from discourse_engine.analyzers.hidden_agenda import HiddenAgendaAnalyzer
from discourse_engine.analyzers.satire import SatireAnalyzer
from discourse_engine.models.report import Report
from discourse_engine.models.config import Config


def run_pipeline(text: str, config: Config | None = None, context_note: str | None = None) -> Report:
    """Run the full analysis pipeline on text and return a Report."""
    if config is None:
        config = Config()

    # Preprocess transcript-style text when markers like [Applause], [Laughter] are present
    if re.search(r"\[[\w\s]+\]", text) and context_note is None:
        from discourse_engine.utils.youtube import preprocess_transcript, detect_comedic_context

        context_note = detect_comedic_context(text)
        text = preprocess_transcript(text)

    satire_prob, satire_signals, content_type = SatireAnalyzer().analyze(text)

    stats = StatisticsAnalyzer().analyze(text)
    trigger = TriggerProfileAnalyzer(lexicon_dir=config.lexicon_dir).analyze(text)
    tone = ToneAnalyzer().analyze(text)
    modal_pronoun = ModalPronounAnalyzer().analyze(text)
    fallacies = LogicalFallacyAnalyzer().analyze(text)
    assumptions = HiddenAssumptionExtractor(
        api_key=config.llm_api_key, model=config.llm_model
    ).analyze(text)
    agenda_flags = HiddenAgendaAnalyzer(lexicon_dir=config.lexicon_dir).analyze(text)

    return Report(
        word_count=stats[0],
        sentence_count=stats[1],
        trigger_profile=trigger,
        tone=tone,
        modal_verbs_detected=modal_pronoun.modal_verbs,
        pronoun_framing=modal_pronoun.pronoun_framing,
        pronoun_insight=modal_pronoun.pronoun_insight,
        logical_fallacy_flags=fallacies,
        hidden_assumptions=assumptions,
        hidden_agenda_flags=agenda_flags,
        context_note=context_note,
        satire_probability=satire_prob,
        content_type_hint=content_type,
    )


def format_report(report: Report) -> str:
    """Format a Report as a human-readable string matching the example output."""
    lines = [
        "--- Discourse Analysis Report ---",
        "",
    ]
    if report.context_note:
        lines.extend([f"Note: {report.context_note}", ""])

    # Content type / satire detection
    lines.extend([
        "Content Type:",
        f"- {report.content_type_hint}",
        f"- Satire/Hyperbole probability: {report.satire_probability:.0%}",
        "",
    ])
    if report.satire_probability >= 0.6:
        lines.extend([
            "Note: High satire probability - flagged patterns may reflect mockery or "
            "exaggeration rather than genuine persuasion. Interpret with caution.",
            "",
        ])

    lines.extend([
        f"Word Count: {report.word_count}",
        f"Sentence Count: {report.sentence_count}",
        "",
        "Trigger Profile:",
        f"- Fear Language: {report.trigger_profile.fear_level}",
        f"- Authority Language: {report.trigger_profile.authority_level}",
        f"- Identity Framing: {report.trigger_profile.identity_level}",
        "",
        "Modal Verbs Detected:",
    ])
    if report.modal_verbs_detected:
        lines.append("- " + ", ".join(report.modal_verbs_detected))
    else:
        lines.append("- (none)")

    lines.extend(["", "Pronoun Framing:"])
    if report.pronoun_framing:
        for k, v in report.pronoun_framing.items():
            lines.append(f'- "{k}": {v}')
        if report.pronoun_insight:
            lines.append(f"-> {report.pronoun_insight}")
    else:
        lines.append("- (none)")

    lines.extend(["", "Logical Fallacy Flags:"])
    if report.logical_fallacy_flags:
        for f in report.logical_fallacy_flags:
            conf_str = f" [{f.confidence:.0%}]" if f.confidence > 0 else ""
            lines.append(f"- {f.name}{conf_str} ({f.pattern_hint})")
            lines.append(f'  -> "{f.sentence}"')
    else:
        lines.append("- (none)")

    lines.extend(["", "Hidden Assumptions:"])
    if report.hidden_assumptions:
        for a in report.hidden_assumptions:
            conf_str = f" [{a.confidence:.0%}]" if a.confidence > 0 else ""
            lines.append(f"- {a.description}{conf_str}")
            lines.append(f'  -> "{a.sentence}"')
    else:
        lines.append("- (none)")

    lines.extend(["", "Hidden Agenda Flags:"])
    if report.hidden_agenda_flags:
        for f in report.hidden_agenda_flags:
            conf_str = f" [{f.confidence:.0%}]" if f.confidence > 0 else ""
            lines.append(f"- {f.family} / {f.technique}{conf_str} ({f.pattern_hint})")
            lines.append(f'  -> "{f.sentence}"')
    else:
        lines.append("- (none)")

    lines.extend(["", "Tone:"])
    if report.tone:
        lines.append("- " + ", ".join(report.tone))
    else:
        lines.append("- (none)")

    return "\n".join(lines)
