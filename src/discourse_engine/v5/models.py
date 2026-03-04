"""Unified semantic graph models for V5 discourse analysis.

The V5 layer represents discourse as a graph:
- Nodes: documents, scenes, speakers/characters, turns, topics.
- Edges: typed relations between nodes (e.g. speaks_in, introduces_topic).
- Timelines: implicit via scene indices and turn indices.

These dataclasses are intentionally JSON-serializable and lightweight so
they can be used both from Python and exported for visualization.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class GraphNode:
    """Generic node in the discourse graph.

    kind: one of {"document", "scene", "speaker", "topic", "turn"}.
    id: globally unique within a DiscourseMap (e.g. "doc:0", "scene:0:1").
    """

    id: str
    kind: str
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Typed relation between two nodes.

    kind examples:
    - "speaks_in"           (speaker -> scene)
    - "turn_in_scene"       (turn -> scene)
    - "introduces_topic"    (speaker -> topic)
    - "mentions_topic"      (turn -> topic)
    - "responds_to_topic"   (turn -> topic)
    - "scene_in_document"   (scene -> document)
    - "influences"          (speaker -> speaker)
    """

    source: str
    target: str
    kind: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Scene:
    """Coherent segment of a document (dialogue or narrative).

    sentence_start / sentence_end are indices into the document's sentence list.
    scene_type: "narrative", "dialogue", "mixed", or other labels.
    """

    id: str
    document_id: str
    index: int
    sentence_start: int
    sentence_end: int
    scene_type: str

    # Speaker / character context
    dominant_speakers: List[str] = field(default_factory=list)

    # Narrative perspective / focalization (lightweight heuristics in v5 phase 1)
    pov: Optional[str] = None  # e.g. "first_person", "third_person", "mixed"
    focalizer: Optional[str] = None  # character_id or "narrator"

    # Pragmatic and narrative signals (placeholders can be refined later)
    irony_score: float = 0.0           # 0-1, higher = more incongruity
    reliability_score: float = 0.5     # 0-1, higher = more reliable narrator
    emotional_intensity: float = 0.0   # 0-1 aggregate

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TopicOwnershipStats:
    """Aggregated metrics for how a speaker or character handles topics."""

    introduced: int = 0
    reframed: int = 0
    responded: int = 0

    @property
    def ownership_ratio(self) -> float:
        total = self.introduced + self.reframed + self.responded
        if total == 0:
            return 0.0
        return self.introduced / total


@dataclass
class CharacterProfile:
    """Cross-document persona profile for Library mode."""

    character_id: str
    display_name: Optional[str] = None

    # Topic ownership across documents
    topic_stats: Dict[str, TopicOwnershipStats] = field(default_factory=dict)

    # Tactical signature (high-level summary fields; can be refined later)
    coercive_turns: int = 0
    defensive_turns: int = 0
    fact_based_turns: int = 0

    documents: List[str] = field(default_factory=list)  # document_ids where seen

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscourseMap:
    """Top-level V5 semantic graph for one or more documents.

    This structure is designed to be:
    - Easy to build incrementally during analysis.
    - Easy to export as JSON (via `to_dict`).
    """

    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)

    # Convenience indexes
    scenes: List[Scene] = field(default_factory=list)
    character_profiles: Dict[str, CharacterProfile] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def add_scene(self, scene: Scene) -> None:
        self.scenes.append(scene)
        # Mirror as a node for graph operations.
        self.add_node(
            GraphNode(
                id=scene.id,
                kind="scene",
                label=f"Scene {scene.index}",
                metadata={
                    "document_id": scene.document_id,
                    "sentence_start": scene.sentence_start,
                    "sentence_end": scene.sentence_end,
                    "scene_type": scene.scene_type,
                    "pov": scene.pov,
                    "focalizer": scene.focalizer,
                    "irony_score": scene.irony_score,
                    "reliability_score": scene.reliability_score,
                    "emotional_intensity": scene.emotional_intensity,
                },
            )
        )

    def get_or_create_character(self, character_id: str, display_name: Optional[str] = None) -> CharacterProfile:
        profile = self.character_profiles.get(character_id)
        if profile is None:
            profile = CharacterProfile(character_id=character_id, display_name=display_name)
            self.character_profiles[character_id] = profile
            self.add_node(
                GraphNode(
                    id=f"speaker:{character_id}",
                    kind="speaker",
                    label=display_name or character_id,
                )
            )
        elif display_name and not profile.display_name:
            profile.display_name = display_name
        return profile

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the discourse map."""
        return {
            "nodes": {node_id: asdict(node) for node_id, node in self.nodes.items()},
            "edges": [asdict(e) for e in self.edges],
            "scenes": [asdict(s) for s in self.scenes],
            "character_profiles": {
                cid: asdict(profile) for cid, profile in self.character_profiles.items()
            },
            "metadata": self.metadata,
        }

