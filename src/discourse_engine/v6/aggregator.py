"""V6 batch/library aggregation helpers.

This module provides:

- A Library Persona Engine that summarizes cross-document speaker behavior
  (median evasion, top fallacies, document-level trends) from a `DiscourseMap`.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any, Dict

from discourse_engine.v5.models import DiscourseMap


def build_library_persona_report(dm: DiscourseMap) -> Dict[str, Any]:
    """Build a cross-document persona summary from a combined `DiscourseMap`.

    The report focuses on:
    - Global Speaker Registry (one entry per character_id).
    - Median evasion score across all appearances (when available).
    - Top 3 fallacies by count across the entire library.
    - Per-document evasion averages to enable "is becoming more evasive over time?"
      style questions downstream.
    """
    speakers: Dict[str, Any] = {}

    for cid, profile in dm.character_profiles.items():
        meta = profile.metadata or {}
        evasion_scores = meta.get("evasion_scores") or []
        fallacy_counts = meta.get("fallacy_counts") or {}
        evasion_by_document = meta.get("evasion_by_document") or {}

        median_evasion = None
        if evasion_scores:
            # Ensure numeric and sort-safe.
            try:
                median_evasion = float(median(float(s) for s in evasion_scores))
            except Exception:
                median_evasion = None

        # Top 3 fallacies by total count.
        top_fallacies = []
        if isinstance(fallacy_counts, dict):
            sorted_fallacies = sorted(
                fallacy_counts.items(),
                key=lambda kv: kv[1],
                reverse=True,
            )
            for ftype, count in sorted_fallacies[:3]:
                top_fallacies.append(
                    {
                        "fallacy_type": ftype,
                        "count": int(count),
                    }
                )

        speakers[cid] = {
            "character_id": cid,
            "display_name": profile.display_name,
            "documents": list(profile.documents),
            "coercive_turns": profile.coercive_turns,
            "defensive_turns": profile.defensive_turns,
            "fact_based_turns": profile.fact_based_turns,
            "median_evasion": median_evasion,
            "evasion_by_document": {
                doc_id: float(score) for doc_id, score in evasion_by_document.items()
            }
            if isinstance(evasion_by_document, dict)
            else {},
            "top_fallacies": top_fallacies,
        }

    return {
        "speakers": speakers,
        "documents": list(dm.metadata.get("documents", [])),
    }


def export_library_persona_report(dm: DiscourseMap, path: str | Path) -> None:
    """Export the library persona report to JSON."""
    report = build_library_persona_report(dm)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

