"""
Centralized constants for the Obsidian MCP server.

This module contains all magic numbers and configuration constants
that are used across the codebase. Centralizing them here makes it
easier to find, modify, and document them.
"""

from typing import Final

# =============================================================================
# Semantic Search Constants
# =============================================================================


class SemanticDefaults:
    """Default values for semantic search operations."""

    # Chunking settings for document splitting
    CHUNK_SIZE: Final[int] = 1500
    CHUNK_OVERLAP: Final[int] = 300

    # Retrieval settings
    VECTOR_K: Final[int] = 12  # Number of vectors to retrieve
    BM25_K: Final[int] = 10  # Number of BM25 results

    # Connection suggestions
    DEFAULT_THRESHOLD: Final[float] = 0.70
    DEFAULT_MIN_WORDS: Final[int] = 150
    DEFAULT_CONNECTION_LIMIT: Final[int] = 10
    TIMEOUT_SECONDS: Final[int] = 180


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
CHUNK_SIZE = SemanticDefaults.CHUNK_SIZE
CHUNK_OVERLAP = SemanticDefaults.CHUNK_OVERLAP
VECTOR_K = SemanticDefaults.VECTOR_K
DEFAULT_THRESHOLD = SemanticDefaults.DEFAULT_THRESHOLD
DEFAULT_MIN_WORDS = SemanticDefaults.DEFAULT_MIN_WORDS
TIMEOUT_SECONDS = SemanticDefaults.TIMEOUT_SECONDS
MAX_SEARCH_RESULTS = SearchLimits.MAX_SEARCH_RESULTS
