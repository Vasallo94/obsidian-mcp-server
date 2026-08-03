"""
Security utilities for path validation and access control.

Provides protection against path traversal attacks and
proper validation of restricted folder access.
"""

import fnmatch
import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import List, Optional, Tuple

from ..config import get_vault_path

logger = logging.getLogger(__name__)

# Cache for forbidden patterns
_forbidden_patterns: Optional[List[str]] = None  # pylint: disable=invalid-name
_forbidden_patterns_vault: Optional[Path] = None  # pylint: disable=invalid-name


class PathSecurityError(Exception):
    """Raised when a path security violation is detected."""


class AccessDeniedError(Exception):
    """Raised when access to a forbidden path is attempted."""


def load_forbidden_patterns(
    force_reload: bool = False, vault_path: Optional[Path] = None
) -> List[str]:
    """Load and merge packaged, vault, and profile path protections."""
    global _forbidden_patterns, _forbidden_patterns_vault  # pylint: disable=global-statement

    if vault_path is None:
        vault_path = get_vault_path()
    resolved_vault = vault_path.resolve() if vault_path else None
    if (
        _forbidden_patterns is not None
        and _forbidden_patterns_vault == resolved_vault
        and not force_reload
    ):
        return _forbidden_patterns

    patterns: List[str] = []
    locations = [Path(__file__).parent.parent.parent / ".forbidden_paths"]
    if vault_path:
        locations.append(vault_path / ".forbidden_paths")

    for location in locations:
        try:
            lines = location.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            logger.debug("Could not read '%s': %s", location, exc)
            continue
        for line in lines:
            pattern = line.strip()
            if pattern and not pattern.startswith("#") and pattern not in patterns:
                patterns.append(pattern)

    # Import here to avoid a module-level cycle with vault_config.
    from ..vault_config import (
        get_vault_config,  # pylint: disable=import-outside-toplevel # noqa: PLC0415
    )

    if vault_path:
        config = get_vault_config(vault_path)
        private_patterns = config.private_paths if config else []
        for pattern in private_patterns or ["**/Privado/*", "**/Private/*"]:
            if pattern not in patterns:
                patterns.append(pattern)

    _forbidden_patterns = patterns
    _forbidden_patterns_vault = resolved_vault
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
        patterns = load_forbidden_patterns(vault_path=vault_path)

        for pattern in patterns:
            # Handle ** patterns (recursive glob)
            if "**" in pattern:
                # Convert ** to work with fnmatch
                # **/ matches any directory depth
                pattern_parts = pattern.split("**")
                if len(pattern_parts) == 2:
                    _, suffix = pattern_parts
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

    except (ValueError, AttributeError) as e:
        return True, f"Error checking path: {e}"  # Fail safe


def check_path_access(
    path: Path | str,
    vault_path: Optional[Path] = None,
    operation: str = "access",
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
        return False, f"Security error: {error}"

    # Second: check if path is forbidden
    is_forbidden, _ = is_path_forbidden(path, vault_path)
    if is_forbidden:
        return False, f"Access denied: cannot {operation} protected paths"

    return True, ""


def resolve_vault_path(
    path: Path | str,
    vault_path: Optional[Path] = None,
    operation: str = "access",
) -> Tuple[Optional[Path], str]:
    """Resolve an allowed path inside the vault without touching the filesystem."""
    if vault_path is None:
        vault_path = get_vault_path()
    if not vault_path:
        return None, "Security error: Vault path not configured"

    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = vault_path / candidate
    is_allowed, error = check_path_access(candidate, vault_path, operation)
    if not is_allowed:
        return None, error
    return candidate.resolve(), ""


def iter_safe_vault_files(
    vault_path: Path,
    pattern: str = "*.md",
    root: Optional[Path] = None,
) -> Iterator[Path]:
    """Yield regular vault files that pass the centralized access policy."""
    scan_root, _ = resolve_vault_path(root or vault_path, vault_path, "scan")
    if scan_root is None or not scan_root.is_dir():
        return

    for current, dirnames, filenames in os.walk(scan_root, followlinks=False):
        current_path = Path(current)
        # Do not descend through directory symlinks or paths outside the policy.
        dirnames[:] = [
            name
            for name in dirnames
            if not (current_path / name).is_symlink()
            and check_path_access(current_path / name, vault_path, "scan")[0]
        ]
        for name in filenames:
            candidate = current_path / name
            if (
                fnmatch.fnmatch(name, pattern)
                and candidate.is_file()
                and not candidate.is_symlink()
                and check_path_access(candidate, vault_path, "scan")[0]
            ):
                yield candidate


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

    except (ValueError, OSError) as e:
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

    except (ValueError, OSError):
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

    except (ValueError, OSError):
        return None
