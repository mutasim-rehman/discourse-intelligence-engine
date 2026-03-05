"""Mermaid.js export utility for V5 discourse maps.

Usage (from repo root):

    py -m discourse_engine.v5.mermaid exports/social_audit.json > social_audit.mmd

This reads a v5-map JSON export and emits a Mermaid graph describing:
- Speaker nodes.
- Co-occurrence edges.
- Alliance edges (aligns_with).
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict


def _sanitize_id(node_id: str) -> str:
    """Convert arbitrary node ids to Mermaid-safe identifiers."""
    # Strip prefix like "speaker:" and replace non-alphanumerics with '_'.
    node_id = re.sub(r"^[^:]+:", "", node_id)
    node_id = re.sub(r"[^A-Za-z0-9_]", "_", node_id)
    if not node_id:
        return "n"
    if not re.match(r"[A-Za-z_]", node_id[0]):
        node_id = "n_" + node_id
    return node_id


def discourse_map_to_mermaid(data: Dict[str, Any]) -> str:
    nodes = data.get("nodes", {})
    edges = data.get("edges", [])
    views = data.get("views", {})
    social = views.get("social_graph", {})
    alliances = social.get("alliances") or []

    # Speaker nodes
    speaker_nodes: Dict[str, Dict[str, str]] = {}
    for node_id, node in nodes.items():
        if node.get("kind") == "speaker":
            speaker_nodes[node_id] = {
                "id": _sanitize_id(node_id),
                "label": node.get("label") or node_id,
            }

    # Co-occurrence edges between speakers
    co_edges = []
    for e in edges:
        if e.get("kind") == "co_occurs_in_scene":
            src, tgt = e.get("source"), e.get("target")
            if src in speaker_nodes and tgt in speaker_nodes:
                co_edges.append((src, tgt))

    lines = ["graph TD"]

    # Declare nodes
    for node_id, meta in speaker_nodes.items():
        lines.append(f"    {meta['id']}[{meta['label']}]")

    # Co-occurrence as light, unlabeled arrows
    for src, tgt in co_edges:
        sid = speaker_nodes[src]["id"]
        tid = speaker_nodes[tgt]["id"]
        lines.append(f"    {sid} --> {tid}")

    # Alliances (aligns_with) as labeled edges
    for edge in alliances:
        src = edge.get("source")
        tgt = edge.get("target")
        if not src or not tgt:
            continue
        if src not in speaker_nodes or tgt not in speaker_nodes:
            continue
        sid = speaker_nodes[src]["id"]
        tid = speaker_nodes[tgt]["id"]
        lines.append(f"    {sid} -- \"Aligns With\" --> {tid}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m discourse_engine.v5.mermaid <v5_map_json_path>", file=sys.stderr)
        sys.exit(1)

    path = argv[0]
    if not os.path.exists(path):
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mermaid = discourse_map_to_mermaid(data)
    print(mermaid)


if __name__ == "__main__":
    main()

