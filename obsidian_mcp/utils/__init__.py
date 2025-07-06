"""
Utilidades compartidas para el servidor MCP de Obsidian
"""

from .logging import get_logger, setup_logging
from .vault import (
    extract_internal_links,
    extract_tags_from_content,
    find_note_by_name,
    format_file_size,
    get_note_metadata,
    get_vault_stats,
    sanitize_filename,
)

__all__ = [
    "get_logger",
    "setup_logging",
    "extract_internal_links",
    "extract_tags_from_content",
    "find_note_by_name",
    "format_file_size",
    "get_note_metadata",
    "get_vault_stats",
    "sanitize_filename",
]
