"""
Security utilities for path validation and access control.

Provides protection against path traversal attacks and
proper validation of restricted folder access.
"""

import fnmatch
import logging
import os
import re
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import List, Optional, Tuple

from ..config import get_vault_path

logger = logging.getLogger(__name__)

# Cache for forbidden patterns
# (vault, patterns) as one tuple so readers never pair one vault's patterns
# with another vault's key.
_forbidden_cache: Optional[Tuple[Optional[Path], List[str]]] = None  # pylint: disable=invalid-name


class PathSecurityError(Exception):
    """Raised when a path security violation is detected."""


class AccessDeniedError(Exception):
    """Raised when access to a forbidden path is attempted."""


def load_forbidden_patterns(
    force_reload: bool = False, vault_path: Optional[Path] = None
) -> List[str]:
    """Load and merge packaged, vault, and profile path protections."""
    global _forbidden_cache  # pylint: disable=global-statement

    if vault_path is None:
        vault_path = get_vault_path()
    resolved_vault = vault_path.resolve() if vault_path else None
    # Read the cache once: another thread may invalidate it between the check
    # and the return.
    cached = _forbidden_cache
    if cached is not None and cached[0] == resolved_vault and not force_reload:
        return cached[1]

    patterns: List[str] = []
    locations = [Path(__file__).parent.parent / ".forbidden_paths"]
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

    _forbidden_cache = (resolved_vault, patterns)
    return patterns


def _normalise_pattern(pattern: str) -> str:
    """Canonical form of a protection pattern.

    Hand-written vault.yaml patterns may carry spaces, a leading "/" or "./",
    or a trailing "/" ("Privado/**/"). Paths are vault-relative and never end
    in "/", so a trailing slash means "the folder and everything below".
    """
    pattern = unicodedata.normalize("NFC", pattern.replace("\\", "/")).strip()
    pattern = re.sub(r"/{2,}", "/", pattern)
    while pattern.startswith(("./", "/")):
        pattern = pattern[2:] if pattern.startswith("./") else pattern[1:]
    if pattern.endswith("/"):
        stripped = pattern.rstrip("/")
        pattern = f"{stripped}/**" if stripped else ""
    return pattern


def _double_star_variants(pattern: str) -> list[str]:
    """Expand ``**`` segments into plain fnmatch patterns.

    ``**/`` and ``/**/`` mean "zero or more folders" and ``/**`` at the end
    means "the folder and everything below". fnmatch's ``*`` already crosses
    ``/``, so each case becomes the zero-folder variant plus a ``*`` variant.
    Matching stays in fnmatch, which keeps its character classes, DOTALL and
    case rules identical to the non-``**`` patterns.
    """
    variants = [pattern]
    for old, zero, many in (("**/", "", "*/"), ("/**/", "/", "/*/")):
        expanded = []
        for v in variants:
            if old == "**/" and v.startswith(old):
                rest = v[len(old) :]
                expanded += [zero + rest, many + rest]
            elif old == "/**/" and old in v:
                # Expand every occurrence, not just the first: a leftover
                # "/**/" would demand at least one folder (fail-open).
                pending = [v]
                while any(old in w for w in pending):
                    pending = [
                        x
                        for w in pending
                        for x in (
                            (w.replace(old, zero, 1), w.replace(old, many, 1))
                            if old in w
                            else (w,)
                        )
                    ]
                expanded += pending
            else:
                expanded.append(v)
        variants = expanded
    result = []
    for v in variants:
        if v.endswith("/**"):
            result += [v[: -len("/**")], v[: -len("**")] + "*"]
        else:
            result.append(v)
    return result


def invalidate_forbidden_patterns_cache() -> None:
    """Drop the cached protection patterns (e.g. after vault.yaml changes)."""
    global _forbidden_cache  # pylint: disable=global-statement
    _forbidden_cache = None


def _pattern_matches(relative_str: str, pattern: str) -> bool:
    """Match one already-normalised pattern against a vault-relative path."""
    if not pattern:
        return False  # an empty pattern must never cover the whole vault
    if "**" in pattern:
        return any(
            fnmatch.fnmatchcase(relative_str, v) for v in _double_star_variants(pattern)
        )
    if fnmatch.fnmatchcase(relative_str, pattern):
        return True
    if not any(char in pattern for char in "*?[") and relative_str.startswith(
        f"{pattern.rstrip('/')}/"
    ):
        return True
    return pattern.endswith("*") and relative_str.startswith(pattern.rstrip("*"))


def _matching_forbidden_pattern(relative_path: Path, patterns: List[str]) -> str:
    """Return the first forbidden pattern matching a normalized vault path.

    Each pattern is tried as written and in its tidied form, and the path is
    denied if either matches: tidying ("Privado//", " **/Privado/*") may add
    protection but can never remove it.
    """
    # NFC on both sides: APFS keeps file names as written (often NFD) while
    # vault.yaml patterns are usually NFC.
    # casefold on both sides: APFS (and NTFS) are case-insensitive, so
    # "privado/x.md" opens the same file as "Privado/x.md". Failing closed.
    # The case-preserving form is always tried too: casefold can change string
    # lengths ("ß" -> "ss"), so a casefold-only match could drop a "?" match.
    relative_str = unicodedata.normalize("NFC", relative_path.as_posix())
    relative_folded = relative_str.casefold()
    for original_pattern in patterns:
        as_written = unicodedata.normalize("NFC", original_pattern.replace("\\", "/"))
        tidied = _normalise_pattern(original_pattern)
        if any(
            _pattern_matches(path, pattern)
            for path, pattern in (
                (relative_str, as_written),
                (relative_str, tidied),
                (relative_folded, as_written.casefold()),
                (relative_folded, tidied.casefold()),
            )
        ):
            return original_pattern
    return ""


def is_path_forbidden(
    path: Path | str,
    vault_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Check a canonical vault-relative path against all protection patterns."""
    if vault_path is None:
        vault_path = get_vault_path()
    if not vault_path:
        return True, "Vault not configured"

    try:
        resolved_vault = vault_path.resolve()
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = resolved_vault / candidate
        relative_path = candidate.resolve().relative_to(resolved_vault)
        pattern = _matching_forbidden_pattern(
            relative_path,
            load_forbidden_patterns(vault_path=resolved_vault),
        )
        return bool(pattern), pattern
    except (ValueError, OSError, AttributeError) as exc:
        return True, f"Error checking path: {exc}"


def check_path_access(
    path: Path | str,
    vault_path: Optional[Path] = None,
    operation: str = "access",
) -> Tuple[bool, str]:
    """Validate the canonical path and apply the vault protection policy."""
    if vault_path is None:
        vault_path = get_vault_path()
    if not vault_path:
        return False, "Security error: Vault path not configured"

    try:
        resolved_vault = vault_path.resolve()
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = resolved_vault / candidate
        relative_path = candidate.resolve().relative_to(resolved_vault)
    except (ValueError, OSError) as exc:
        return False, f"Security error: Path escapes vault directory: {exc}"

    pattern = _matching_forbidden_pattern(
        relative_path,
        load_forbidden_patterns(vault_path=resolved_vault),
    )
    if pattern:
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

    resolved_vault = vault_path.resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = resolved_vault / candidate
    candidate = candidate.resolve()
    is_allowed, error = check_path_access(candidate, resolved_vault, operation)
    if not is_allowed:
        return None, error
    return candidate, ""


def iter_safe_vault_files(
    vault_path: Path,
    pattern: str = "*.md",
    root: Optional[Path] = None,
) -> Iterator[Path]:
    """Yield allowed vault files with policy data resolved once per scan."""
    resolved_vault = vault_path.resolve()
    scan_root, _ = resolve_vault_path(root or resolved_vault, resolved_vault, "scan")
    if scan_root is None or not scan_root.is_dir():
        return
    patterns = load_forbidden_patterns(vault_path=resolved_vault)

    for current, dirnames, filenames in os.walk(scan_root, followlinks=False):
        current_path = Path(current)
        safe_directories: list[str] = []
        for name in dirnames:
            candidate = current_path / name
            if candidate.is_symlink():
                continue
            relative = candidate.relative_to(resolved_vault)
            if not _matching_forbidden_pattern(relative, patterns):
                safe_directories.append(name)
        dirnames[:] = safe_directories

        for name in filenames:
            if not fnmatch.fnmatch(name, pattern):
                continue
            candidate = current_path / name
            resolved_candidate = (
                candidate.resolve() if candidate.is_symlink() else candidate
            )
            try:
                relative = resolved_candidate.relative_to(resolved_vault)
            except ValueError:
                continue
            if resolved_candidate.is_file() and not _matching_forbidden_pattern(
                relative, patterns
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
