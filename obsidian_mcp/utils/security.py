"""
Security utilities for path validation and access control.

Provides protection against path traversal attacks and
proper validation of restricted folder access.
"""

import fnmatch
from pathlib import Path
from typing import List, Optional, Tuple

from ..config import get_vault_path, get_vault_settings

# Cache for forbidden patterns
_forbidden_patterns: Optional[List[str]] = None


class PathSecurityError(Exception):
    """Raised when a path security violation is detected."""

    pass


class AccessDeniedError(Exception):
    """Raised when access to a forbidden path is attempted."""

    pass


def load_forbidden_patterns(force_reload: bool = False) -> List[str]:
    """
    Load forbidden path patterns from .forbidden_paths file.

    Args:
        force_reload: If True, reload from file even if cached.

    Returns:
        List of glob patterns for forbidden paths.
    """
    global _forbidden_patterns

    if _forbidden_patterns is not None and not force_reload:
        return _forbidden_patterns

    patterns: List[str] = []

    # Try to load from project root first, then from vault
    possible_locations = [
        Path(__file__).parent.parent.parent / ".forbidden_paths",  # Project root
    ]

    vault_path = get_vault_path()
    if vault_path:
        possible_locations.append(vault_path / ".forbidden_paths")

    for location in possible_locations:
        if location.exists():
            try:
                with open(location, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            patterns.append(line)
                break  # Use first found file
            except Exception:
                continue

    # Always include private folder from settings as fallback
    settings = get_vault_settings()
    private_pattern = f"{settings.private_folder}/*"
    if private_pattern not in patterns:
        patterns.append(private_pattern)

    _forbidden_patterns = patterns
    return patterns


def is_path_forbidden(
    path: Path | str,
    vault_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Check if a path matches any forbidden pattern.

    Args:
        path: Path to check (absolute or relative to vault)
        vault_path: The vault root path. If None, retrieved from config.

    Returns:
        Tuple of (is_forbidden, matched_pattern)
    """
    if vault_path is None:
        vault_path = get_vault_path()

    if not vault_path:
        return True, "Vault not configured"  # Fail safe

    try:
        if isinstance(path, str):
            path = Path(path)

        # Make path relative to vault for pattern matching
        if path.is_absolute():
            try:
                relative_path = path.relative_to(vault_path)
            except ValueError:
                # Path is not under vault
                return True, "Path outside vault"
        else:
            relative_path = path

        relative_str = str(relative_path)
        patterns = load_forbidden_patterns()

        for pattern in patterns:
            # Handle ** patterns (recursive glob)
            if "**" in pattern:
                # Convert ** to work with fnmatch
                # **/ matches any directory depth
                pattern_parts = pattern.split("**")
                if len(pattern_parts) == 2:
                    prefix, suffix = pattern_parts
                    suffix = suffix.lstrip("/")
                    # Check if the path ends with the suffix pattern
                    if fnmatch.fnmatch(relative_str, f"*{suffix}"):
                        return True, pattern
                    # Also check just the filename
                    if fnmatch.fnmatch(relative_path.name, suffix.lstrip("*")):
                        return True, pattern
            else:
                # Simple glob pattern
                if fnmatch.fnmatch(relative_str, pattern):
                    return True, pattern
                # Also try matching with path starting with pattern base
                if relative_str.startswith(pattern.rstrip("*")):
                    return True, pattern

        return False, ""

    except Exception as e:
        return True, f"Error checking path: {e}"  # Fail safe


def check_path_access(
    path: Path | str,
    vault_path: Optional[Path] = None,
    operation: str = "acceder a",
) -> Tuple[bool, str]:
    """
    Centralized access check for all path operations.
    Combines path validation within vault and forbidden path checking.

    Args:
        path: Path to check
        vault_path: The vault root path
        operation: Description of the operation (for error message)

    Returns:
        Tuple of (is_allowed, error_message)
        If is_allowed is True, error_message is empty.
        If is_allowed is False, error_message contains the denial reason.
    """
    if vault_path is None:
        vault_path = get_vault_path()

    # First: validate path is within vault
    is_valid, error = validate_path_within_vault(path, vault_path)
    if not is_valid:
        return False, f"⛔ Error de seguridad: {error}"

    # Second: check if path is forbidden
    is_forbidden, pattern = is_path_forbidden(path, vault_path)
    if is_forbidden:
        return False, f"⛔ ACCESO DENEGADO: No se permite {operation} rutas protegidas"

    return True, ""


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
