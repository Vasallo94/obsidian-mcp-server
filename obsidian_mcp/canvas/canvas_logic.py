"""
Logic for generic canvas tools.

Provides CRUD operations on any .canvas file without workflow assumptions.
All functions return Result[str].
"""

from __future__ import annotations

from pathlib import Path

from ..config import get_vault_path
from ..result import Result
from ..utils import get_logger
from . import engine
from .models import CanvasFile, Edge, Node, describe_canvas_colors

logger = get_logger(__name__)


def _resolve_canvas_path(canvas_path: str) -> Result[str]:
    """Resolve a canvas path relative to vault root.

    Returns Result with the absolute path string on success.
    """
    vault_path = get_vault_path()
    if vault_path is None:
        return Result.fail("Vault path is not configured.")

    abs_path = Path(canvas_path)
    if not abs_path.is_absolute():
        abs_path = vault_path / canvas_path

    if abs_path.suffix != ".canvas":
        return Result.fail(f"Not a .canvas file: {canvas_path}")

    return Result.ok(str(abs_path))


def _load(canvas_path: str) -> Result[CanvasFile]:
    """Load a canvas with path resolution and error handling."""
    resolved = _resolve_canvas_path(canvas_path)
    if not resolved.success:
        return Result.fail(resolved.error)  # type: ignore[arg-type]

    try:
        canvas = engine.load_canvas(resolved.data)  # type: ignore[arg-type]
        return Result.ok(canvas)
    except FileNotFoundError:
        return Result.fail(f"Canvas file not found: {canvas_path}")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return Result.fail(f"Error loading canvas: {exc}")


def _save(canvas: CanvasFile) -> Result[str]:
    """Save canvas with error handling."""
    try:
        engine.save_canvas(canvas)
        return Result.ok("saved")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return Result.fail(f"Error saving canvas: {exc}")


def _format_node_summary(node: Node) -> str:
    """Format a node for display."""
    if node.type == "group":
        return f"  [{node.id}] GROUP: {node.label}"
    label = node.text.split("\n")[0][:60] if node.text else "(empty)"
    color = f" color={node.color}" if node.color else ""
    return f"  [{node.id}] {label}{color}"


def _find_legend_card(text_nodes: list[Node]) -> Node | None:
    """Return a card that looks like a color legend, if any.

    A legend card is a text node whose first heading line mentions
    "legend" or "leyenda". Surfacing it lets agents follow the board's
    color convention instead of guessing (AFP issue #49).
    """
    for node in text_nodes:
        first_line = node.text.split("\n", 1)[0].lower() if node.text else ""
        if first_line.startswith("#") and (
            "legend" in first_line or "leyenda" in first_line
        ):
            return node
    return None


def read_canvas(canvas_path: str) -> Result[str]:
    """Read a canvas and return a human-readable summary."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    groups = engine.find_nodes_by_type(canvas, "group")  # type: ignore[arg-type]
    text_nodes = engine.find_nodes_by_type(canvas, "text")  # type: ignore[arg-type]

    lines = [
        f"Canvas: {canvas_path}",
        f"Nodes: {len(canvas.nodes)} | Edges: {len(canvas.edges)}",  # type: ignore[union-attr]
        "",
    ]

    if groups:
        lines.append("Groups:")
        for g in groups:
            lines.append(f"  [{g.id}] {g.label}")
        lines.append("")

    if text_nodes:
        lines.append("Cards:")
        for n in text_nodes:
            lines.append(_format_node_summary(n))
        lines.append("")

    if canvas.edges:  # type: ignore[union-attr]
        lines.append("Edges:")
        for e in canvas.edges:  # type: ignore[union-attr]
            lines.append(f"  [{e.id}] {e.from_node} → {e.to_node}")
        lines.append("")

    lines.append(f"Colors (Obsidian standard): {describe_canvas_colors()}")
    legend = _find_legend_card(text_nodes)
    if legend is not None:
        lines.append("")
        lines.append(f"Board legend (card [{legend.id}]):")
        for legend_line in legend.text.splitlines():
            lines.append(f"  {legend_line}")

    return Result.ok("\n".join(lines))


def list_canvases(folder: str) -> Result[str]:
    """List all .canvas files in the vault or a subfolder."""
    vault_path = get_vault_path()
    if vault_path is None:
        return Result.fail("Vault path is not configured.")

    search_path = vault_path / folder if folder else vault_path
    if not search_path.is_dir():
        return Result.fail(f"Folder not found: {folder}")

    canvas_files = sorted(search_path.rglob("*.canvas"))
    if not canvas_files:
        return Result.ok("No .canvas files found.")

    lines = [f"Found {len(canvas_files)} canvas file(s):"]
    for f in canvas_files:
        rel = f.relative_to(vault_path)
        lines.append(f"  {rel}")

    return Result.ok("\n".join(lines))


def add_card(  # pylint: disable=too-many-positional-arguments
    canvas_path: str,
    text: str,
    group: str = "",
    color: str = "",
    width: int = 280,
    height: int = 160,
) -> Result[str]:
    """Add a text card to a canvas."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    group_node = None

    if group:
        groups = engine.find_nodes_by_type(canvas, "group")  # type: ignore[arg-type]
        group_node = next((g for g in groups if g.label == group), None)
        if group_node is None:
            return Result.fail(f"Group '{group}' not found in canvas.")

    x, y = engine.compute_node_placement(canvas, group_node, [])  # type: ignore[arg-type]
    new_node = Node(
        id=engine.generate_node_id(),
        type="text",
        x=x,
        y=y,
        width=width,
        height=height,
        text=text,
        color=color,
    )
    engine.add_node(canvas, new_node)  # type: ignore[arg-type]

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    logger.info("Added card [%s] to canvas %s", new_node.id, canvas_path)
    return Result.ok(f"Card added: [{new_node.id}] {text[:50]}")


def add_group(canvas_path: str, label: str) -> Result[str]:
    """Add a group to a canvas."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    existing = engine.find_nodes_by_type(canvas, "group")  # type: ignore[arg-type]
    x = 0
    if existing:
        rightmost = max(existing, key=lambda g: g.x + g.width)
        x = rightmost.x + rightmost.width + 50

    new_group = Node(
        id=engine.generate_node_id(),
        type="group",
        x=x,
        y=0,
        width=400,
        height=800,
        label=label,
    )
    engine.add_node(canvas, new_group)  # type: ignore[arg-type]

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    logger.info("Added group [%s] '%s' to canvas %s", new_group.id, label, canvas_path)
    return Result.ok(f"Group added: [{new_group.id}] {label}")


def add_canvas_edge(
    canvas_path: str,
    from_id: str,
    to_id: str,
    label: str = "",
) -> Result[str]:
    """Add an edge between two nodes."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    from_node = engine.find_node(canvas, from_id)  # type: ignore[arg-type]
    if from_node is None:
        return Result.fail(f"Source node '{from_id}' not found.")
    to_node = engine.find_node(canvas, to_id)  # type: ignore[arg-type]
    if to_node is None:
        return Result.fail(f"Target node '{to_id}' not found.")

    if engine.has_cycle(canvas, from_id, to_id):  # type: ignore[arg-type]
        return Result.fail(f"Adding edge {from_id} → {to_id} would create a cycle.")

    from_side, to_side = engine.pick_edge_sides(from_node, to_node)
    new_edge = Edge(
        id=engine.generate_edge_id(),
        from_node=from_id,
        to_node=to_id,
        from_side=from_side,
        to_side=to_side,
        label=label,
    )
    engine.add_edge(canvas, new_edge)  # type: ignore[arg-type]

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    return Result.ok(f"Edge added: {from_id} → {to_id}")


def update_card(
    canvas_path: str,
    node_id: str,
    text: str = "",
    color: str = "",
) -> Result[str]:
    """Update text and/or color of a card."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    node = engine.find_node(canvas, node_id)  # type: ignore[arg-type]
    if node is None:
        return Result.fail(f"Node '{node_id}' not found.")

    changes: dict[str, str] = {}
    if text:
        changes["text"] = text
    if color:
        changes["color"] = color

    if not changes:
        return Result.ok("No changes specified.")

    engine.update_node(canvas, node_id, **changes)  # type: ignore[arg-type]

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    return Result.ok(f"Card [{node_id}] updated.")


def move_card(canvas_path: str, node_id: str, x: int, y: int) -> Result[str]:
    """Reposition a node by setting its absolute x/y coordinates."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    node = engine.find_node(canvas, node_id)  # type: ignore[arg-type]
    if node is None:
        return Result.fail(f"Node '{node_id}' not found.")

    engine.update_node(canvas, node_id, x=x, y=y)  # type: ignore[arg-type]

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    return Result.ok(f"Node [{node_id}] moved to ({x}, {y}).")


def remove_group(
    canvas_path: str,
    group_id: str,
    remove_contents: bool = False,
) -> Result[str]:
    """Remove a group node.

    By default only the group container is removed and the cards it visually
    contained stay on the canvas. Pass ``remove_contents=True`` to also delete
    every node inside the group's bounding box (and their edges).
    """
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    group = engine.find_node(canvas, group_id)  # type: ignore[arg-type]
    if group is None:
        return Result.fail(f"Group '{group_id}' not found.")
    if group.type != "group":
        return Result.fail(f"Node '{group_id}' is not a group.")

    removed_contents = 0
    if remove_contents:
        contained = [
            n
            for n in canvas.nodes  # type: ignore[union-attr]
            if n.id != group_id and engine.find_group_for_node(canvas, n) is group  # type: ignore[arg-type]
        ]
        for node in contained:
            engine.remove_node(canvas, node.id)  # type: ignore[arg-type]
            removed_contents += 1

    engine.remove_node(canvas, group_id)  # type: ignore[arg-type]

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    if removed_contents:
        return Result.ok(
            f"Group [{group_id}] removed along with {removed_contents} card(s)."
        )
    return Result.ok(f"Group [{group_id}] removed.")


def remove_card(canvas_path: str, node_id: str) -> Result[str]:
    """Remove a card and its connected edges."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    try:
        engine.remove_node(canvas, node_id)  # type: ignore[arg-type]
    except ValueError as exc:
        return Result.fail(str(exc))

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    return Result.ok(f"Card [{node_id}] removed.")


def remove_canvas_edge(canvas_path: str, edge_id: str) -> Result[str]:
    """Remove an edge."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    try:
        engine.remove_edge(canvas, edge_id)  # type: ignore[arg-type]
    except ValueError as exc:
        return Result.fail(str(exc))

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    return Result.ok(f"Edge [{edge_id}] removed.")
