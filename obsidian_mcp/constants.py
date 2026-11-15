"""
Centralized constants for the Obsidian MCP server.

This module contains all magic numbers and configuration constants
that are used across the codebase. Centralizing them here makes it
easier to find, modify, and document them.
"""

from typing import Final

# =============================================================================
# Search and Display Limits
# =============================================================================


class SearchLimits:
    """Limits for search operations and result display."""

    MAX_SEARCH_RESULTS: Final[int] = 100
    MAX_DISPLAY_FILES: Final[int] = 20
    MAX_CONTEXT_LINES: Final[int] = 2
    MAX_LINE_LENGTH: Final[int] = 100
    MIN_NOTE_SIZE_BYTES: Final[int] = 200


# =============================================================================
# Folder Suggestion Constants
# =============================================================================


class FolderSuggestion:
    """Constants for folder suggestion functionality."""

    SIMILAR_NOTES_LIMIT: Final[int] = 5
    TOP_K_SUGGESTIONS: Final[int] = 3
    HIGH_CONFIDENCE_THRESHOLD: Final[float] = 0.5


# =============================================================================
# File and Path Constants
# =============================================================================


class FileConstants:
    """File-related constants."""

    YOUTUBE_VIDEO_ID_LENGTH: Final[int] = 11
    MAX_FRAGMENT_LENGTH: Final[int] = 300
    MIN_PARAGRAPH_LENGTH: Final[int] = 50


# =============================================================================
# Backward Compatibility - Direct exports
# =============================================================================

# These are exported for backward compatibility with existing code
MAX_SEARCH_RESULTS = SearchLimits.MAX_SEARCH_RESULTS
