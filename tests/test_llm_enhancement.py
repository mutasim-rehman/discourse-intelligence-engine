"""Tests for LLM enhancement module (mock-based, no API required)."""

from unittest.mock import patch

from discourse_engine.models.report import AssumptionFlag, TriggerProfile
from discourse_engine.llm_enhancement import enhance_assumptions, enhance_satire_irony


def test_enhance_assumptions_returns_unchanged_when_llm_fails() -> None:
    """When LLM returns None, candidates are returned unchanged."""
    candidates = [
        AssumptionFlag(description="Test", sentence="x", confidence=0.8),
    ]
    result = enhance_assumptions("Some text with must and require.", candidates)
    assert result == candidates


def test_enhance_assumptions_skips_when_many_candidates() -> None:
    """When len(candidates) >= 3, no LLM call (returns as-is)."""
    candidates = [
        AssumptionFlag(description="A", sentence="", confidence=0.7),
        AssumptionFlag(description="B", sentence="", confidence=0.7),
        AssumptionFlag(description="C", sentence="", confidence=0.7),
    ]
    result = enhance_assumptions("Text with must.", candidates)
    assert result == candidates
    assert len(result) == 3


def test_enhance_assumptions_skips_when_not_argumentative() -> None:
    """When no argumentative signals, returns as-is."""
    candidates: list[AssumptionFlag] = []
    result = enhance_assumptions("The sky is blue. Grass is green.", candidates)
    assert result == candidates


def test_enhance_assumptions_parses_numbered_list() -> None:
    """When LLM returns numbered list, new assumptions are added."""
    with patch("discourse_engine.llm_enhancement._call_llm") as mock_llm:
        mock_llm.return_value = (
            "1. Investment leads to positive outcomes.\n"
            "2. Audits ensure accountability."
        )
        candidates: list[AssumptionFlag] = []
        result = enhance_assumptions(
            "We must increase investment. Audits will evaluate.",
            candidates,
        )
        assert len(result) >= 2
        llm_added = [a for a in result if a.description.startswith("LLM:")]
        assert len(llm_added) >= 1


def test_enhance_satire_irony_returns_base_when_outside_range() -> None:
    """When base_prob < 0.2 or > 0.5, returns unchanged."""
    prob, sigs = enhance_satire_irony("Text", 0.1, [])
    assert prob == 0.1
    assert sigs == []

    prob2, sigs2 = enhance_satire_irony("Text", 0.8, [{"name": "x"}])
    assert prob2 == 0.8
    assert sigs2 == [{"name": "x"}]


def test_enhance_satire_irony_returns_base_when_llm_fails() -> None:
    """When LLM returns None, base probability is returned."""
    prob, sigs = enhance_satire_irony("Ironic text here.", 0.3, [])
    assert prob == 0.3


def test_enhance_satire_irony_blends_with_llm() -> None:
    """When LLM returns probability, result is blended."""
    with patch("discourse_engine.llm_enhancement._call_llm") as mock_llm:
        mock_llm.return_value = "75\nThis text mocks authoritarian language."
        prob, sigs = enhance_satire_irony("Ironic text.", 0.35, [])
        assert prob > 0.35
        assert prob <= 0.95


def test_enhance_satire_irony_incongruity_rule_forces_ambiguous() -> None:
    """High Fear + High Authority + concrete nouns (hair dryer) forces prob into 0.35 for LLM."""
    trigger = TriggerProfile(fear_level="High", authority_level="High", identity_level="Moderate")
    text = "The tropospheric containment field failed. We need industrial hair dryers to mitigate."
    with patch("discourse_engine.llm_enhancement._call_llm") as mock_llm:
        mock_llm.return_value = "85\nClearly satirical - hair dryers for atmospheric failure."
        prob, _ = enhance_satire_irony(text, 0.0, [], trigger_profile=trigger)
        assert mock_llm.called
        assert prob > 0.5


def test_enhance_assumptions_corporate_euphemisms_trigger_llm() -> None:
    """Corporate terms (initiative, strategic) trigger LLM even without modals."""
    candidates: list[AssumptionFlag] = []
    text = "Our Right-Sizing Initiative represents a strategic pivot to streamline the ecosystem."
    with patch("discourse_engine.llm_enhancement._call_llm") as mock_llm:
        mock_llm.return_value = "1. Layoffs are acceptable for shareholder value."
        result = enhance_assumptions(text, candidates)
        assert mock_llm.called
        assert len(result) >= 1
