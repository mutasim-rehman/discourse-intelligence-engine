"""V5 Discourse Map visualization helpers.

These utilities provide lightweight, JSON-friendly views on top of the
`DiscourseMap` graph that can be rendered by external tools (D3, Plotly,
networkx, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from discourse_engine.v5.models import DiscourseMap


def social_graph_view(dm: DiscourseMap) -> Dict[str, Any]:
    """Return a simplified social graph view over speakers.

    Nodes: speakers with basic metadata.
    Edges: co-occurrence edges. Alliances: aligns_with (e.g. "I agree with X").
    """
    nodes = []
    edges: Dict[tuple[str, str], float] = {}
    alliances: list[Dict[str, Any]] = []

    for node_id, node in dm.nodes.items():
        if node.kind == "speaker":
            nodes.append(
                {
                    "id": node_id,
                    "label": node.label or node_id,
                    "metadata": node.metadata,
                }
            )

    for edge in dm.edges:
        if edge.kind == "co_occurs_in_scene":
            key = (edge.source, edge.target)
            edges[key] = edges.get(key, 0.0) + edge.weight
        elif edge.kind == "aligns_with":
            alliances.append({
                "source": edge.source,
                "target": edge.target,
                "weight": edge.weight,
                "metadata": edge.metadata,
            })

    edge_list = [
        {"source": src, "target": tgt, "weight": weight}
        for (src, tgt), weight in edges.items()
    ]

    return {
        "nodes": nodes,
        "edges": edge_list,
        "alliances": alliances,
    }


def export_discourse_map(dm: DiscourseMap, path: str | Path) -> None:
    """Export the full discourse map (plus a default social view) to JSON."""
    data = dm.to_dict()
    data.setdefault("views", {})
    data["views"]["social_graph"] = social_graph_view(dm)

    path = Path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

