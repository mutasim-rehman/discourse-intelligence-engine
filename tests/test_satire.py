"""Tests for satire detection."""

import pytest

from discourse_engine.analyzers.satire import SatireAnalyzer


def test_satire_detects_cats_example() -> None:
    """The classic 'ruled by cats' example is flagged as satire."""
    text = (
        "If we allow one small policy change, the universe will collapse "
        "and society will turn into chaos ruled by cats."
    )
    prob, signals, content_type = SatireAnalyzer().analyze(text)
    assert prob >= 0.6
    assert "Satire" in content_type or "Hyperbole" in content_type
    assert len(signals) >= 1


def test_genuine_argument_low_satire() -> None:
    """Genuine political argument gets low satire probability."""
    text = (
        "Either we pass this law, or our nation will collapse. "
        "We must protect our people from this growing threat."
    )
    prob, _, content_type = SatireAnalyzer().analyze(text)
    assert prob < 0.6
    assert "Genuine" in content_type or "low" in content_type.lower()


def test_empty_text_returns_zero() -> None:
    """Empty text returns zero probability."""
    prob, signals, content_type = SatireAnalyzer().analyze("")
    assert prob == 0.0
    assert signals == []
    assert content_type == "Uncertain"


def test_self_undermining_contradiction() -> None:
    """Self-undermining text is flagged."""
    text = "This policy is perfect because it completely ignores facts, data, and common sense."
    prob, signals, _ = SatireAnalyzer().analyze(text)
    assert prob >= 0.5
    assert any(s.name == "Self-undermining" for s in signals)
