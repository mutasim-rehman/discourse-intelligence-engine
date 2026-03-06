"""Mermaid.js export utility for V5 discourse maps.

Usage (from repo root):

    py -m discourse_engine.v5.mermaid exports/social_audit.json > exports/social_audit.mmd

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

    labeled_edges: list[tuple[str, str, str]] = []
    co_edges: list[tuple[str, str]] = []

    for e in edges:
        kind = e.get("kind")
        src, tgt = e.get("source"), e.get("target")
        if not src or not tgt:
            continue
        if src not in speaker_nodes or tgt not in speaker_nodes:
            continue

        if kind == "responds_to":
            ev = None
            meta = e.get("metadata") or {}
            if isinstance(meta, dict):
                ev = meta.get("evasion_score")
            if isinstance(ev, (int, float)):
                label = f"Answers (evasion={ev:.2f})"
            else:
                label = "Answers"
            labeled_edges.append((src, tgt, label))
        elif kind == "aligns_with":
            labeled_edges.append((src, tgt, "Aligns With"))
        elif kind == "follows":
            labeled_edges.append((src, tgt, "Responds"))
        elif kind == "co_occurs_in_scene":
            co_edges.append((src, tgt))

    lines = ["graph TD"]

    # Declare nodes
    for node_id, meta in speaker_nodes.items():
        lines.append(f"    {meta['id']}[{meta['label']}]")

    # Prefer labeled interaction edges; only fall back to co-occurrence when nothing else exists.
    if labeled_edges:
        # Deduplicate: collapse repeated edges into a single labeled edge.
        counts: Dict[tuple[str, str, str], int] = {}
        for src, tgt, label in labeled_edges:
            counts[(src, tgt, label)] = counts.get((src, tgt, label), 0) + 1
        for (src, tgt, label), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1], kv[0][2])):
            sid = speaker_nodes[src]["id"]
            tid = speaker_nodes[tgt]["id"]
            edge_label = label if n == 1 else f"{label} x{n}"
            lines.append(f"    {sid} -- \"{edge_label}\" --> {tid}")
    else:
        for src, tgt in co_edges:
            sid = speaker_nodes[src]["id"]
            tid = speaker_nodes[tgt]["id"]
            lines.append(f"    {sid} --> {tid}")

    # Alliances view (legacy): keep rendering if present and not already added.
    existing_pairs = {(s, t) for (s, t, _lbl) in labeled_edges}
    for edge in alliances:
        src = edge.get("source")
        tgt = edge.get("target")
        if not src or not tgt:
            continue
        if src not in speaker_nodes or tgt not in speaker_nodes:
            continue
        if (src, tgt) in existing_pairs:
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

