"""V5 semantic graph and advanced discourse analysis utilities.

This package introduces:
- A unified semantic graph model (`DiscourseMap`) for documents, scenes,
  speakers/characters, topics, and discourse relations.
- Scene-level analysis utilities (scene detection, topic ownership, etc.).
- Library-mode aggregation across multiple documents.

The goal is to provide a single, JSON-serializable representation that can
back visualizations and higher-level research workflows.
"""

from .models import (
    GraphNode,
    GraphEdge,
    Scene,
    CharacterProfile,
    TopicOwnershipStats,
    DiscourseMap,
)

__all__ = [
    "GraphNode",
    "GraphEdge",
    "Scene",
    "CharacterProfile",
    "TopicOwnershipStats",
    "DiscourseMap",
]

