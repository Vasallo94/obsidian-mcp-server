"""MCP graph and connection tools for Obsidian vaults."""

from fastmcp import FastMCP

from .graph_logic import (
    find_orphan_notes as find_orphan_notes_logic,
)
from .graph_logic import (
    get_backlinks as get_backlinks_logic,
)
from .graph_logic import (
    get_local_graph as get_local_graph_logic,
)
from .graph_logic import (
    get_notes_by_tag as get_notes_by_tag_logic,
)
from .registry import register_tool


def register_graph_tools(mcp: FastMCP) -> None:
    """Register graph and relationship tools."""

    @register_tool(mcp, "get_backlinks")
    def get_backlinks(note_path: str) -> str:
        """List notes that link to the given note."""
        try:
            return get_backlinks_logic(note_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error reading backlinks: {e}"

    @register_tool(mcp, "get_notes_by_tag")
    def get_notes_by_tag(tag: str) -> str:
        """List notes that contain a specific tag."""
        try:
            return get_notes_by_tag_logic(tag).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error finding notes by tag: {e}"

    @register_tool(mcp, "get_local_graph")
    def get_local_graph(note_path: str, depth: int = 1) -> str:
        """Read incoming and outgoing links around a note."""
        try:
            return get_local_graph_logic(note_path, depth).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error reading local graph: {e}"

    @register_tool(mcp, "find_orphan_notes")
    def find_orphan_notes() -> str:
        """Find notes without incoming or outgoing wikilinks."""
        try:
            return find_orphan_notes_logic().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error finding orphan notes: {e}"
