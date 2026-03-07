"""Dialogue-level power dynamics analysis.

Derives per-speaker dominance and authority metrics from DialogueTurns.
"""

from __future__ import annotations

import re
from collections import defaultdict

from discourse_engine.v4.models import Dialogue, PowerDynamicsSummary, SpeakerPowerMetrics


INTENSITY_TERMS = {
    "must",
    "need",
    "urgent",
    "critical",
    "crisis",
    "protect",
    "defend",
    "threat",
    "attack",
    "fear",
    "danger",
    "never",
    "always",
    "certain",
    "absolute",
    "everyone",
    "destroy",
    "collapse",
}
DOMINANCE_TERMS = {"must", "shall", "will", "cannot", "never", "always", "everyone"}
CERTAINTY_MODALS = {"must", "will", "shall", "cannot"}


def _intensity_score(text: str) -> float:
    lower = text.lower()
    words = re.findall(r"\b\w+\b", lower)
    if not words:
        return 0.0
    count = sum(1 for w in words if w in INTENSITY_TERMS)
    return min(count / len(words) * 10, 1.0)


def _dominance_score(text: str) -> float:
    lower = text.lower()
    words = lower.split()
    if not words:
        return 0.0
    count = sum(1 for w in words if re.sub(r"\W", "", w) in DOMINANCE_TERMS)
    return min(count / len(words) * 5, 1.0)


def _certainty_score(text: str) -> float:
    lower = text.lower()
    words = lower.split()
    if not words:
        return 0.0
    count = sum(1 for w in words if re.sub(r"\W", "", w) in CERTAINTY_MODALS)
    return min(count / len(words) * 8, 1.0)


class PowerDynamicsAnalyzer:
    """Aggregates dominance / authority metrics per speaker."""

    def analyze(self, dialogue: Dialogue) -> PowerDynamicsSummary:
        turns = dialogue.turns
        if not turns:
            return PowerDynamicsSummary(speakers=[], summary="No turns to analyze.")

        per_speaker: dict[str, dict[str, float | int]] = defaultdict(
            lambda: {
                "total_turns": 0,
                "total_tokens": 0,
                "interruption_count": 0,
                "sum_intensity": 0.0,
                "sum_dominance": 0.0,
                "sum_certainty": 0.0,
                "title_prior": 0.0,
            }
        )

        for idx, t in enumerate(turns):
            text = t.text or ""
            tokens = text.split()
            intensity = _intensity_score(text)
            dominance = _dominance_score(text)
            certainty = _certainty_score(text)

            stats = per_speaker[t.speaker_id]
            stats["total_turns"] += 1
            stats["total_tokens"] += len(tokens)
            stats["sum_intensity"] += intensity
            stats["sum_dominance"] += dominance
            stats["sum_certainty"] += certainty

            # Very lightweight interruption heuristic: short turn that immediately follows a different speaker.
            if idx > 0:
                prev = turns[idx - 1]
                if prev.speaker_id != t.speaker_id and len(tokens) > 0 and len(tokens) <= 10:
                    stats["interruption_count"] += 1

        # Title-based authority priors from speaker display names.
        TITLE_WEIGHTS = {
            "ceo": 1.0,
            "chief executive officer": 1.0,
            "minister": 0.95,
            "high overseer": 0.95,
            "general": 0.9,
            "director": 0.85,
            "chair": 0.85,
            "chairperson": 0.85,
            "president": 0.9,
            "manager": 0.7,
            "auditor": 0.65,
        }

        for speaker_id, profile in (dialogue.speaker_profiles or {}).items():
            display = (profile.display_name or "").lower()
            prior = 0.0
            for title, weight in TITLE_WEIGHTS.items():
                if title in display:
                    prior = max(prior, weight)
            if prior > 0.0:
                per_speaker[speaker_id]["title_prior"] = prior

        metrics: list[SpeakerPowerMetrics] = []
        for speaker_id, stats in per_speaker.items():
            total_turns = int(stats["total_turns"])
            if total_turns == 0:
                continue
            avg_intensity = stats["sum_intensity"] / total_turns
            avg_dominance = stats["sum_dominance"] / total_turns
            avg_certainty = stats["sum_certainty"] / total_turns
            title_prior = float(stats["title_prior"])

            dominance_score = min(avg_intensity + 0.5 * avg_dominance, 1.0)
            # Blend certainty-based authority with title-based prior so that a quiet CEO
            # still appears more authoritative than a loud Manager.
            blended = avg_certainty
            if title_prior > 0.0:
                blended = (avg_certainty + 0.5 * title_prior) / 1.5
            authority_score = min(blended, 1.0)

            metrics.append(
                SpeakerPowerMetrics(
                    speaker_id=speaker_id,
                    total_turns=total_turns,
                    total_tokens=int(stats["total_tokens"]),
                    interruption_count=int(stats["interruption_count"]),
                    authority_score=authority_score,
                    dominance_score=dominance_score,
                )
            )

        # Normalize dominance/authority so that the most dominant/authoritative speaker ≈ 1.0.
        if metrics:
            max_dom = max(m.dominance_score for m in metrics) or 1.0
            max_auth = max(m.authority_score for m in metrics) or 1.0
            for m in metrics:
                m.dominance_score = m.dominance_score / max_dom if max_dom > 0 else 0.0
                m.authority_score = m.authority_score / max_auth if max_auth > 0 else 0.0

        # Sort speakers by dominance descending for readability
        metrics.sort(key=lambda m: m.dominance_score, reverse=True)

        if metrics:
            leader = metrics[0]
            summary = (
                f"Most dominant speaker: {leader.speaker_id} "
                f"(dominance={leader.dominance_score:.2f}, authority={leader.authority_score:.2f})."
            )
        else:
            summary = "No speaker dominance could be computed."

        return PowerDynamicsSummary(speakers=metrics, summary=summary)

