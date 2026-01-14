"""
Security utilities for path validation and access control.

Provides protection against path traversal attacks and
proper validation of restricted folder access.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from ..config import get_vault_path


class PathSecurityError(Exception):
    """Raised when a path security violation is detected."""

    pass


def validate_path_within_vault(
    path: Path | str,
    vault_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Validates that a path is within the vault directory.
    Prevents path traversal attacks (../, symlinks escaping vault).

    Args:
        path: The path to validate (relative or absolute)
        vault_path: The vault root path. If None, retrieved from config.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if vault_path is None:
        vault_path = get_vault_path()

    if not vault_path:
        return False, "Vault path not configured"

    try:
        # Convert to Path if string
        if isinstance(path, str):
            path = Path(path)

        # If relative, join with vault path first
        if not path.is_absolute():
            path = vault_path / path

        # Resolve to canonical path (handles .., symlinks)
        resolved_path = path.resolve()
        resolved_vault = vault_path.resolve()

        # Check if resolved path is under vault using is_relative_to (Python 3.9+)
        if not resolved_path.is_relative_to(resolved_vault):
            return False, f"Path escapes vault directory: {path}"

        return True, ""

    except Exception as e:
        return False, f"Path validation error: {e}"


def is_path_in_restricted_folder(
    path: Path | str,
    restricted_folders: List[str],
    vault_path: Optional[Path] = None,
) -> bool:
    """
    Check if path is in a restricted folder.
    Uses proper path comparison, not string matching.

    Args:
        path: Path to check
        restricted_folders: List of restricted folder paths relative to vault
        vault_path: Vault root path

    Returns:
        True if path is in a restricted folder
    """
    if vault_path is None:
        vault_path = get_vault_path()

    if not vault_path:
        return True  # Fail safe - deny if no vault path

    try:
        if isinstance(path, str):
            path = Path(path)

        if not path.is_absolute():
            path = vault_path / path

        resolved_path = path.resolve()

        for folder in restricted_folders:
            restricted_path = (vault_path / folder).resolve()
            # Check if the path is under the restricted folder
            if resolved_path.is_relative_to(restricted_path):
                return True

        return False

    except Exception:
        return True  # Fail safe - deny on error


def get_safe_relative_path(
    path: Path | str,
    vault_path: Optional[Path] = None,
) -> Optional[str]:
    """
    Get a safe relative path within the vault.

    Args:
        path: The path to make relative
        vault_path: The vault root path

    Returns:
        Relative path string if safe, None if unsafe
    """
    if vault_path is None:
        vault_path = get_vault_path()

    if not vault_path:
        return None

    is_valid, _ = validate_path_within_vault(path, vault_path)
    if not is_valid:
        return None

    try:
        if isinstance(path, str):
            path = Path(path)

        if not path.is_absolute():
            path = vault_path / path

        return str(path.resolve().relative_to(vault_path.resolve()))

    except Exception:
        return None
