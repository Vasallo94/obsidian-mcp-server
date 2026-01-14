"""
Pydantic models for structured data in Obsidian MCP Server.
"""

from .responses import (
    ConnectionSuggestion,
    NoteMetadata,
    SearchResult,
    SemanticSearchResult,
    VaultStats,
)

__all__ = [
    "ConnectionSuggestion",
    "NoteMetadata",
    "SearchResult",
    "SemanticSearchResult",
    "VaultStats",
]
