"""
Generic canvas MCP tools.

Provides CRUD operations on any .canvas file in the vault.
No workflow assumptions — these tools work with any canvas
(mind maps, diagrams, project boards, etc.).
"""

from fastmcp import FastMCP

from ..middleware import enrich_response
from ..tools.registry import register_tool
from ..utils import get_logger
from .canvas_logic import (
    add_canvas_edge,
    add_card,
    add_group,
    list_canvases,
    move_card,
    read_canvas,
    remove_canvas_edge,
    remove_card,
    remove_group,
    update_card,
)

logger = get_logger(__name__)


def register_canvas_tools(mcp: FastMCP) -> None:
    """Register generic canvas tools with the MCP server."""

    @register_tool(mcp, "canvas.read")
    def canvas_read(canvas_path: str) -> str:
        """Read a canvas file and return a human-readable summary of its nodes, edges, and groups.

        Args:
            canvas_path: Path to the .canvas file (relative to vault root or absolute)

        Returns:
            Summary of canvas contents
        """
        try:
            return read_canvas(canvas_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error reading canvas: {e}"

    @register_tool(mcp, "canvas.list")
    def canvas_list(folder: str = "") -> str:
        """List all .canvas files in the vault or in a specific folder.

        Args:
            folder: Subfolder to search in (relative to vault root). Empty for entire vault.

        Returns:
            List of .canvas file paths
        """
        try:
            return list_canvases(folder).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error listing canvases: {e}"

    @register_tool(mcp, "canvas.add_card")
    def canvas_add_card(
        canvas_path: str,
        text: str,
        group: str = "",
        color: str = "",
        width: int = 280,
        height: int = 160,
    ) -> str:
        """Add a text card to a canvas file.

        Standard Obsidian canvas colors: "0"=default (gray), "1"=red,
        "2"=orange, "3"=yellow, "4"=green, "5"=cyan, "6"=purple. A board may
        define its own color->status convention in a "Legend" card — call
        canvas_read first to see it before choosing a color.

        Card text is validated against the vault rules (e.g. no emojis in
        headings); any violations are reported alongside the confirmation.

        Args:
            canvas_path: Path to the .canvas file
            text: Card text content
            group: Name of group to place the card in (optional)
            color: Card color as string "0"-"6" (optional, see legend above)
            width: Card width in pixels (default 280)
            height: Card height in pixels (default 160)

        Returns:
            Confirmation with the new card ID
        """
        try:
            result = add_card(
                canvas_path, text, group, color, width, height
            ).to_display()
            return enrich_response(
                tool_name="canvas.add_card",
                result=result,
                content=text,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error adding card: {e}"

    @register_tool(mcp, "canvas.add_group")
    def canvas_add_group(canvas_path: str, label: str) -> str:
        """Create a new group/area in a canvas file.

        Args:
            canvas_path: Path to the .canvas file
            label: Group label text

        Returns:
            Confirmation with the new group ID
        """
        try:
            return add_group(canvas_path, label).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error adding group: {e}"

    @register_tool(mcp, "canvas.add_edge")
    def canvas_add_edge(
        canvas_path: str,
        from_id: str,
        to_id: str,
        label: str = "",
    ) -> str:
        """Connect two nodes with a directional arrow. Rejects if it would create a cycle.

        Args:
            canvas_path: Path to the .canvas file
            from_id: Source node ID
            to_id: Target node ID
            label: Edge label (optional)

        Returns:
            Confirmation of the new edge
        """
        try:
            return add_canvas_edge(canvas_path, from_id, to_id, label).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error adding edge: {e}"

    @register_tool(mcp, "canvas.update_card")
    def canvas_update_card(
        canvas_path: str,
        node_id: str,
        text: str = "",
        color: str = "",
    ) -> str:
        """Update the text and/or color of an existing card.

        Standard Obsidian canvas colors: "0"=default (gray), "1"=red,
        "2"=orange, "3"=yellow, "4"=green, "5"=cyan, "6"=purple. A board may
        define its own color->status convention in a "Legend" card — call
        canvas_read first to see it.

        New text is validated against the vault rules (e.g. no emojis in
        headings); any violations are reported alongside the confirmation.

        Args:
            canvas_path: Path to the .canvas file
            node_id: ID of the card to update
            text: New text content (leave empty to keep current)
            color: New color "0"-"6" (leave empty to keep current, see legend above)

        Returns:
            Confirmation of the update
        """
        try:
            result = update_card(canvas_path, node_id, text, color).to_display()
            return enrich_response(
                tool_name="canvas.update_card",
                result=result,
                content=text,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error updating card: {e}"

    @register_tool(mcp, "canvas.remove_card")
    def canvas_remove_card(canvas_path: str, node_id: str) -> str:
        """Delete a card and all its connected edges from a canvas.

        Args:
            canvas_path: Path to the .canvas file
            node_id: ID of the card to remove

        Returns:
            Confirmation of removal
        """
        try:
            return remove_card(canvas_path, node_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error removing card: {e}"

    @register_tool(mcp, "canvas.move_card")
    def canvas_move_card(canvas_path: str, node_id: str, x: int, y: int) -> str:
        """Reposition a node by setting its absolute x/y coordinates.

        Works for any node (card or group). Use canvas_read to inspect current
        positions; coordinates grow right (x) and down (y).

        Args:
            canvas_path: Path to the .canvas file
            node_id: ID of the node to move
            x: New x coordinate (pixels)
            y: New y coordinate (pixels)

        Returns:
            Confirmation of the move
        """
        try:
            return move_card(canvas_path, node_id, x, y).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error moving node: {e}"

    @register_tool(mcp, "canvas.remove_group")
    def canvas_remove_group(
        canvas_path: str,
        group_id: str,
        remove_contents: bool = False,
    ) -> str:
        """Delete a group/area from a canvas.

        By default only the group container is removed; the cards it visually
        contained stay on the canvas. Set remove_contents=True to also delete
        every card inside the group's bounding box.

        Args:
            canvas_path: Path to the .canvas file
            group_id: ID of the group to remove
            remove_contents: If True, also delete contained cards (default False)

        Returns:
            Confirmation of removal
        """
        try:
            return remove_group(canvas_path, group_id, remove_contents).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error removing group: {e}"

    @register_tool(mcp, "canvas.remove_edge")
    def canvas_remove_edge(canvas_path: str, edge_id: str) -> str:
        """Delete a connection between two nodes.

        Args:
            canvas_path: Path to the .canvas file
            edge_id: ID of the edge to remove

        Returns:
            Confirmation of removal
        """
        try:
            return remove_canvas_edge(canvas_path, edge_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error removing edge: {e}"
