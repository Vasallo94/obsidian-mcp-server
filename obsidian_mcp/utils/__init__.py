"""
Utilidades compartidas para el servidor MCP de Obsidian
"""

from .logging import get_logger, setup_logging
from .security import (
    AccessDeniedError,
    PathSecurityError,
    check_path_access,
    get_safe_relative_path,
    is_path_forbidden,
    is_path_in_restricted_folder,
    load_forbidden_patterns,
    validate_path_within_vault,
)
from .vault import (
    extract_internal_links,
    extract_tags_from_content,
    find_note_by_name,
    format_file_size,
    get_note_metadata,
    get_vault_stats,
    invalidate_note_cache,
    read_note_async,
    sanitize_filename,
    write_note_async,
)

__all__ = [
    "get_logger",
    "setup_logging",
    "AccessDeniedError",
    "PathSecurityError",
    "check_path_access",
    "get_safe_relative_path",
    "is_path_forbidden",
    "is_path_in_restricted_folder",
    "load_forbidden_patterns",
    "validate_path_within_vault",
    "extract_internal_links",
    "extract_tags_from_content",
    "find_note_by_name",
    "format_file_size",
    "get_note_metadata",
    "get_vault_stats",
    "invalidate_note_cache",
    "read_note_async",
    "sanitize_filename",
    "write_note_async",
]
