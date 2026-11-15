"""
Pydantic models for structured data in Obsidian MCP Server.
"""

from .responses import (
    NoteMetadata,
    SearchResult,
    VaultStats,
)

__all__ = [
    "NoteMetadata",
    "SearchResult",
    "VaultStats",
]
