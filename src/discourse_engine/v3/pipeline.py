"""Unified v3 pipeline and export utilities."""

import json
from pathlib import Path

from discourse_engine.v3.narrative_arc import NarrativeArcAnalyzer
from discourse_engine.v3.contradiction import ContradictionAnalyzer
from discourse_engine.v3.temporal_drift import TemporalDriftAnalyzer
from discourse_engine.v3.debate_heatmap import DebateHeatmapAnalyzer


def run_narrative_arc(text: str, chunk_size: int = 5) -> dict:
    """Run narrative arc analysis and return report + viz data."""
    report = NarrativeArcAnalyzer(chunk_size=chunk_size).analyze(text)
    return {
        "summary": report.summary,
        "escalation_points": report.escalation_points,
        "framing_shifts": [
            {"chunk": c, "framing": f} for c, f in report.dominant_framing_shifts
        ],
        "viz": report.viz_data,
    }


def run_contradiction(turns: list[tuple[str, str]]) -> dict:
    """Run contradiction detection and return report."""
    report = ContradictionAnalyzer().analyze(turns)
    return {
        "summary": report.summary,
        "pairs": [
            {
                "speaker_a": p.speaker_a,
                "speaker_b": p.speaker_b,
                "probability": p.probability,
                "type": p.contradiction_type,
            }
            for p in report.pairs
        ],
        "reframing_detected": report.reframing_detected,
        "evasion_likelihood": report.evasion_likelihood,
    }


def run_temporal_drift(documents: list[tuple[str, str | None, str]]) -> dict:
    """Run temporal drift analysis and return report."""
    report = TemporalDriftAnalyzer().analyze(documents)
    return {
        "summary": report.summary,
        "timeline": report.viz_data.get("timeline", []),
        "viz": report.viz_data,
    }


def run_debate_heatmap(turns: list[tuple[str, str]], time_bins: int = 10) -> dict:
    """Run debate heatmap analysis and return report."""
    report = DebateHeatmapAnalyzer(time_bins=time_bins).analyze(turns)
    return {
        "summary": report.summary,
        "heatmap": report.viz_data.get("heatmap", []),
        "speakers": report.speakers,
        "influence": report.influence_scores,
        "viz": report.viz_data,
    }


def export_viz_to_json(data: dict, path: str | Path) -> None:
    """Export visualization data to JSON for external tools."""
    path = Path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Exported viz data to {path}", flush=True)
