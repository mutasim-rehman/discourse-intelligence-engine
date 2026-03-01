"""Tests for v3 modules."""

import pytest

from discourse_engine.v3 import (
    NarrativeArcAnalyzer,
    ContradictionAnalyzer,
    TemporalDriftAnalyzer,
    DebateHeatmapAnalyzer,
)


def test_narrative_arc_basic() -> None:
    text = "We must act. They threaten us. The danger is real. We will prevail."
    report = NarrativeArcAnalyzer(chunk_size=2).analyze(text)
    assert len(report.chunks) >= 1
    assert report.summary
    assert "viz_data" in report.__dict__ or hasattr(report, "viz_data")
    assert "emotional_intensity" in report.viz_data or "x" in report.viz_data


def test_narrative_arc_empty() -> None:
    report = NarrativeArcAnalyzer().analyze("")
    assert report.chunks == []
    assert "No text" in report.summary


def test_contradiction_basic() -> None:
    turns = [
        ("A", "We never supported that policy."),
        ("B", "They supported it in 2022."),
    ]
    report = ContradictionAnalyzer().analyze(turns)
    assert report.summary
    assert isinstance(report.pairs, list)
    assert isinstance(report.evasion_likelihood, float)


def test_temporal_drift_basic() -> None:
    docs = [
        ("s1", "2023-01", "We need freedom and liberty. The people demand rights."),
        ("s2", "2023-06", "Order and authority must be restored. The law protects us."),
    ]
    report = TemporalDriftAnalyzer().analyze(docs)
    assert len(report.profiles) == 2
    assert len(report.drift_vectors) >= 1
    assert report.profiles[0].liberty > report.profiles[1].liberty
    assert report.profiles[1].authority > report.profiles[0].authority


def test_debate_heatmap_basic() -> None:
    turns = [
        ("Alice", "We must act now. The threat is real."),
        ("Bob", "I disagree. Perhaps we should wait."),
    ]
    report = DebateHeatmapAnalyzer().analyze(turns)
    assert len(report.turns) == 2
    assert report.speakers == ["Alice", "Bob"]
    assert len(report.heatmap_grid) == 2
    assert report.influence_scores["Alice"] >= report.influence_scores["Bob"]
