"""Temporal Rhetoric Drift Tracking.

Tracks how a speaker's rhetorical positioning shifts across multiple documents over time.
"""

import json
from pathlib import Path

from discourse_engine.v3.models import DocumentProfile, DriftVector, TemporalDriftReport


def _load_lexicon(lexicon_dir: Path, name: str) -> list[str]:
    path = lexicon_dir / f"{name}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _count_matches(text: str, terms: list[str]) -> int:
    lower = text.lower()
    return sum(1 for t in terms if t.lower() in lower)


def _score_to_normalized(count: int, word_count: int) -> float:
    if word_count == 0:
        return 0.0
    return min(count / (word_count / 100), 1.0)


class TemporalDriftAnalyzer:
    """
    Tracks rhetorical drift across multiple documents (e.g. same speaker over time).
    """

    def __init__(self, lexicon_dir: Path | None = None) -> None:
        if lexicon_dir is None:
            lexicon_dir = Path(__file__).parent.parent / "lexicons"
        self.lexicon_dir = Path(lexicon_dir)
        self._fear = _load_lexicon(self.lexicon_dir, "fear_terms")
        self._authority = _load_lexicon(self.lexicon_dir, "authority_terms")
        self._identity = _load_lexicon(self.lexicon_dir, "identity_terms")
        self._liberty = _load_lexicon(self.lexicon_dir, "liberty_terms")
        if not self._fear:
            self._fear = ["collapse", "destroy", "threat", "danger", "crisis"]
        if not self._liberty:
            self._liberty = ["freedom", "liberty", "free", "rights", "oppression"]

    def _profile_document(self, doc_id: str, date: str | None, text: str) -> DocumentProfile:
        words = text.split()
        wc = len(words)
        return DocumentProfile(
            doc_id=doc_id,
            date=date,
            fear=_score_to_normalized(_count_matches(text, self._fear), wc),
            authority=_score_to_normalized(_count_matches(text, self._authority), wc),
            identity=_score_to_normalized(_count_matches(text, self._identity), wc),
            liberty=_score_to_normalized(_count_matches(text, self._liberty), wc),
            word_count=wc,
        )

    def analyze(
        self,
        documents: list[tuple[str, str | None, str]],
    ) -> TemporalDriftReport:
        """
        Analyze drift across documents.

        Args:
            documents: [(doc_id, date_or_none, text), ...]
        """
        profiles: list[DocumentProfile] = []
        for doc_id, date, text in documents:
            if text and text.strip():
                profiles.append(self._profile_document(doc_id, date, text))

        drift_vectors: list[DriftVector] = []
        for i in range(len(profiles) - 1):
            p1, p2 = profiles[i], profiles[i + 1]
            for dim in ("fear", "authority", "identity", "liberty"):
                v1 = getattr(p1, dim)
                v2 = getattr(p2, dim)
                delta = v2 - v1
                pct = (delta / (v1 + 0.001)) * 100 if v1 else 0
                drift_vectors.append(
                    DriftVector(
                        dimension=dim,
                        from_value=v1,
                        to_value=v2,
                        delta=delta,
                        pct_change=pct,
                    )
                )

        timeline_data = [
            {
                "doc_id": p.doc_id,
                "date": p.date,
                "fear": p.fear,
                "authority": p.authority,
                "identity": p.identity,
                "liberty": p.liberty,
            }
            for p in profiles
        ]

        summary_parts = [f"Analyzed {len(profiles)} documents."]
        if drift_vectors:
            max_drift = max(drift_vectors, key=lambda d: abs(d.delta))
            summary_parts.append(
                f"Largest shift: {max_drift.dimension} ({max_drift.delta:+.2f})."
            )
        summary = " ".join(summary_parts)

        viz_data = {
            "timeline": timeline_data,
            "dimensions": ["fear", "authority", "identity", "liberty"],
        }

        return TemporalDriftReport(
            profiles=profiles,
            drift_vectors=drift_vectors,
            timeline_data=timeline_data,
            summary=summary,
            viz_data=viz_data,
        )
