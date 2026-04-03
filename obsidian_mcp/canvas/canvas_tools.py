"""
Generic canvas MCP tools.

Provides CRUD operations on any .canvas file in the vault.
No workflow assumptions — these tools work with any canvas
(mind maps, diagrams, project boards, etc.).
"""

from fastmcp import FastMCP

from ..utils import get_logger
from .canvas_logic import (
    add_canvas_edge,
    add_card,
    add_group,
    list_canvases,
    read_canvas,
    remove_canvas_edge,
    remove_card,
    update_card,
)

logger = get_logger(__name__)


def register_canvas_tools(mcp: FastMCP) -> None:
    """Register generic canvas tools with the MCP server."""

    @mcp.tool()
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

    @mcp.tool()
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

    @mcp.tool()
    def canvas_add_card(
        canvas_path: str,
        text: str,
        group: str = "",
        color: str = "",
        dimensions: str = "",
    ) -> str:
        """Add a text card to a canvas file.

        Args:
            canvas_path: Path to the .canvas file
            text: Card text content
            group: Name of group to place the card in (optional)
            color: Card color as string "0"-"6" (optional)
            dimensions: Card dimensions as "WIDTHxHEIGHT" e.g. "280x160" (optional, defaults to 280x160)

        Returns:
            Confirmation with the new card ID
        """
        try:
            width = 280
            height = 160
            if dimensions:
                parts = dimensions.split("x")
                if len(parts) == 2:
                    try:
                        width = int(parts[0])
                        height = int(parts[1])
                    except ValueError:
                        pass
            return add_card(canvas_path, text, group, color, width, height).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error adding card: {e}"

    @mcp.tool()
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

    @mcp.tool()
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

    @mcp.tool()
    def canvas_update_card(
        canvas_path: str,
        node_id: str,
        text: str = "",
        color: str = "",
    ) -> str:
        """Update the text and/or color of an existing card.

        Args:
            canvas_path: Path to the .canvas file
            node_id: ID of the card to update
            text: New text content (leave empty to keep current)
            color: New color "0"-"6" (leave empty to keep current)

        Returns:
            Confirmation of the update
        """
        try:
            return update_card(canvas_path, node_id, text, color).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error updating card: {e}"

    @mcp.tool()
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

    @mcp.tool()
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
