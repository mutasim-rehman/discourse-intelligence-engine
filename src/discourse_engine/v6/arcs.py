"""V6 character and relationship arc data models.

These are lightweight, JSON-ready containers built on top of:
- v4 dialogue reports (turn-level metrics, power dynamics, evasion).
- v5 DiscourseMap (scenes, turns, speakers, semantic drift).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Tuple


@dataclass
class ArcEvent:
    """A notable event in a character or relationship arc (pivot, spike, etc.)."""

    position: float  # 0-1 normalized position within the document or corpus
    label: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CharacterArcPoint:
    """Single point on a character arc timeline."""

    document_id: str
    scene_id: str | None
    turn_index: int | None
    position: float  # 0-1 within this document
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CharacterArc:
    """Full arc for a character across one or more documents."""

    character_id: str
    display_name: str | None = None
    points: List[CharacterArcPoint] = field(default_factory=list)
    events: List[ArcEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "display_name": self.display_name,
            "points": [asdict(p) for p in self.points],
            "events": [asdict(e) for e in self.events],
        }


@dataclass
class RelationshipArcPoint:
    """Interaction snapshot between two characters at a given moment."""

    document_id: str
    scene_id: str | None
    turn_index: int | None
    position: float
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationshipArc:
    """Temporal arc describing how a pair's interaction changes."""

    pair: Tuple[str, str]  # (source_character_id, target_character_id)
    points: List[RelationshipArcPoint] = field(default_factory=list)
    events: List[ArcEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": list(self.pair),
            "points": [asdict(p) for p in self.points],
            "events": [asdict(e) for e in self.events],
        }


def arcs_to_view_payload(
    character_arcs: Dict[str, CharacterArc],
    relationship_arcs: Dict[Tuple[str, str], RelationshipArc] | None = None,
) -> Dict[str, Any]:
    """Convert arcs into a compact JSON view for dashboards."""
    relationship_arcs = relationship_arcs or {}
    return {
        "characters": {
            cid: arc.to_dict() for cid, arc in character_arcs.items()
        },
        "relationships": {
            f"{a}__{b}": rel.to_dict() for (a, b), rel in relationship_arcs.items()
        },
    }

