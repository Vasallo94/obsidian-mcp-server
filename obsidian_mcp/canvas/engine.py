"""
Canvas engine — pure operations on Obsidian Canvas files.

Handles I/O (load/save), queries (find nodes, dependencies, cycles),
and mutations (add/remove/update nodes and edges). No workflow opinion —
this layer knows about canvas structure but not about task states or
workflow rules.

All mutation functions operate in-place on a CanvasFile instance.
The caller decides when to save.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from ..utils import get_logger
from .models import CanvasFile, Edge, Node

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def load_canvas(path: str) -> CanvasFile:
    """Load a .canvas file and return a CanvasFile instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Canvas file not found: {path}")

    raw = file_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    logger.debug(
        "Loaded canvas from %s: %d nodes, %d edges",
        path,
        len(data.get("nodes", [])),
        len(data.get("edges", [])),
    )
    return CanvasFile.from_dict(path, data)


def save_canvas(canvas: CanvasFile) -> None:
    """Write a CanvasFile to disk as JSON."""
    data = canvas.to_dict()
    Path(canvas.path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.debug(
        "Saved canvas to %s: %d nodes, %d edges",
        canvas.path,
        len(canvas.nodes),
        len(canvas.edges),
    )


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


def generate_node_id() -> str:
    """Generate a short unique ID for a new node."""
    return uuid.uuid4().hex[:16]


def generate_edge_id() -> str:
    """Generate a short unique ID for a new edge."""
    return uuid.uuid4().hex[:16]


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def find_node(canvas: CanvasFile, node_id: str) -> Optional[Node]:
    """Find a node by ID. Returns None if not found."""
    for node in canvas.nodes:
        if node.id == node_id:
            return node
    return None


def find_nodes_by_type(canvas: CanvasFile, node_type: str) -> list[Node]:
    """Return all nodes of a given type."""
    return [n for n in canvas.nodes if n.type == node_type]


def find_group_for_node(canvas: CanvasFile, node: Node) -> Optional[Node]:
    """Find the group that visually contains a node (by bounding box)."""
    if node.type == "group":
        return None
    groups = find_nodes_by_type(canvas, "group")
    for group in groups:
        if (
            group.x <= node.x
            and group.y <= node.y
            and group.x + group.width >= node.x + node.width
            and group.y + group.height >= node.y + node.height
        ):
            return group
    return None


def get_dependencies(canvas: CanvasFile, node: Node) -> list[Node]:
    """Get nodes that block this node (inbound edges: fromNode → this node)."""
    dep_ids = [e.from_node for e in canvas.edges if e.to_node == node.id]
    return [n for n in canvas.nodes if n.id in dep_ids]


def get_dependents(canvas: CanvasFile, node: Node) -> list[Node]:
    """Get nodes that this node blocks (outbound edges: this node → toNode)."""
    dep_ids = [e.to_node for e in canvas.edges if e.from_node == node.id]
    return [n for n in canvas.nodes if n.id in dep_ids]


def has_cycle(canvas: CanvasFile, from_id: str, to_id: str) -> bool:
    """Check if adding an edge from_id → to_id would create a cycle.

    A cycle would be created if to_id can already reach from_id via
    existing edges (i.e., there is a path to_id → ... → from_id).
    Uses DFS starting from to_id following existing outgoing edges.
    """
    adj: dict[str, list[str]] = {}
    for edge in canvas.edges:
        adj.setdefault(edge.from_node, []).append(edge.to_node)

    visited: set[str] = set()
    stack = [to_id]
    while stack:
        current = stack.pop()
        if current == from_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        stack.extend(adj.get(current, []))
    return False


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def add_node(canvas: CanvasFile, node: Node) -> Node:
    """Add a node to the canvas."""
    canvas.nodes.append(node)
    return node


def update_node(canvas: CanvasFile, node_id: str, **changes) -> Node:
    """Update attributes of an existing node.

    Raises:
        ValueError: If the node is not found.
    """
    node = find_node(canvas, node_id)
    if node is None:
        raise ValueError(f"Node '{node_id}' not found")
    for key, value in changes.items():
        if hasattr(node, key):
            setattr(node, key, value)
    return node


def remove_node(canvas: CanvasFile, node_id: str) -> None:
    """Remove a node and all its connected edges.

    Raises:
        ValueError: If the node is not found.
    """
    node = find_node(canvas, node_id)
    if node is None:
        raise ValueError(f"Node '{node_id}' not found")
    canvas.nodes.remove(node)
    canvas.edges = [e for e in canvas.edges if node_id not in (e.from_node, e.to_node)]


def add_edge(canvas: CanvasFile, edge: Edge) -> Edge:
    """Add an edge to the canvas."""
    canvas.edges.append(edge)
    return edge


def remove_edge(canvas: CanvasFile, edge_id: str) -> None:
    """Remove an edge by ID.

    Raises:
        ValueError: If the edge is not found.
    """
    for i, edge in enumerate(canvas.edges):
        if edge.id == edge_id:
            canvas.edges.pop(i)
            return
    raise ValueError(f"Edge '{edge_id}' not found")


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------


def compute_node_placement(
    canvas: CanvasFile,
    group: Optional[Node],
    depends_on: list[Node],
) -> tuple[int, int]:
    """Compute x, y position for a new node."""
    if group is not None:
        group_nodes = [
            n
            for n in canvas.nodes
            if n.type != "group" and find_group_for_node(canvas, n) == group
        ]
        if group_nodes:
            lowest = max(group_nodes, key=lambda n: n.y + n.height)
            return group.x + 20, lowest.y + lowest.height + 40
        return group.x + 20, group.y + 60

    if depends_on:
        lowest = max(depends_on, key=lambda n: n.y + n.height)
        return lowest.x, lowest.y + lowest.height + 40

    if canvas.nodes:
        lowest = max(canvas.nodes, key=lambda n: n.y + n.height)
        return lowest.x, lowest.y + lowest.height + 40
    return 0, 0


def pick_edge_sides(from_node: Node, to_node: Node) -> tuple[str, str]:
    """Choose edge attachment sides based on relative node positions."""
    dx = to_node.x - from_node.x
    dy = to_node.y - from_node.y

    if abs(dy) >= abs(dx):
        if dy > 0:
            return "bottom", "top"
        return "top", "bottom"
    if dx > 0:
        return "right", "left"
    return "left", "right"
