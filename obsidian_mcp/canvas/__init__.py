"""
Canvas management module for the Obsidian MCP server.

Provides generic canvas CRUD operations and a Kanvas-inspired
project management workflow with color-coded task states.
"""

from .engine import (
    add_edge,
    add_node,
    compute_node_placement,
    find_group_for_node,
    find_node,
    find_nodes_by_type,
    generate_edge_id,
    generate_node_id,
    get_dependencies,
    get_dependents,
    has_cycle,
    load_canvas,
    pick_edge_sides,
    remove_edge,
    remove_node,
    save_canvas,
    update_node,
)
from .models import (
    TASK_ID_RE,
    CanvasFile,
    Edge,
    KanvasMetadata,
    Node,
    TaskState,
    WorkflowMode,
)

__all__ = [
    "CanvasFile",
    "Edge",
    "KanvasMetadata",
    "Node",
    "TaskState",
    "WorkflowMode",
    "TASK_ID_RE",
    "load_canvas",
    "save_canvas",
    "find_node",
    "find_nodes_by_type",
    "find_group_for_node",
    "get_dependencies",
    "get_dependents",
    "has_cycle",
    "add_node",
    "update_node",
    "remove_node",
    "add_edge",
    "remove_edge",
    "compute_node_placement",
    "pick_edge_sides",
    "generate_node_id",
    "generate_edge_id",
]
