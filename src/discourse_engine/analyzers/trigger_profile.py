"""Trigger word profile analyzer: fear, authority, identity levels."""

import json
from pathlib import Path

from discourse_engine.models.report import TriggerProfile


def _load_lexicon(lexicon_dir: Path, name: str) -> list[str]:
    """Load a JSON lexicon file."""
    path = lexicon_dir / f"{name}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _count_matches(text: str, terms: list[str]) -> int:
    """Count how many terms appear in text (case-insensitive)."""
    lower_text = text.lower()
    return sum(1 for t in terms if t.lower() in lower_text)


def _count_to_level(count: int) -> str:
    """Map count to Low / Moderate / High."""
    if count == 0:
        return "Low"
    if count <= 2:
        return "Moderate"
    return "High"


class TriggerProfileAnalyzer:
    """Analyzes fear, authority, and identity framing levels."""

    def __init__(self, lexicon_dir: Path | None = None) -> None:
        if lexicon_dir is None:
            lexicon_dir = Path(__file__).parent.parent / "lexicons"
        self.lexicon_dir = lexicon_dir
        self._fear = _load_lexicon(lexicon_dir, "fear_terms")
        self._authority = _load_lexicon(lexicon_dir, "authority_terms")
        self._identity = _load_lexicon(lexicon_dir, "identity_terms")

    def analyze(self, text: str) -> TriggerProfile:
        """Return TriggerProfile with fear, authority, identity levels."""
        fear_count = _count_matches(text, self._fear) if self._fear else 0
        authority_count = _count_matches(text, self._authority) if self._authority else 0
        identity_count = _count_matches(text, self._identity) if self._identity else 0
        return TriggerProfile(
            fear_level=_count_to_level(fear_count),
            authority_level=_count_to_level(authority_count),
            identity_level=_count_to_level(identity_count),
        )
