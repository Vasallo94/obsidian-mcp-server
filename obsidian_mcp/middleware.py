"""
Middleware for vault rule enforcement.

Loads machine-readable validations from .agents/REGLAS_GLOBALES.md,
runs checks against content on write operations, and enriches tool
responses with warnings and rule prose.

This is agent-agnostic: any MCP client receives the same enforcement.
"""

import re
from typing import Any

import yaml

from .config import get_vault_path
from .utils import get_logger

logger = get_logger(__name__)

# --- Cache ---

_rules_cache: list[dict[str, Any]] | None = None  # pylint: disable=invalid-name
_prose_cache: str | None = None  # pylint: disable=invalid-name

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


def _read_rules_file() -> tuple[dict[str, Any], str]:
    """Read and parse REGLAS_GLOBALES.md, returning (frontmatter_dict, prose_body)."""
    vault_path = get_vault_path()
    if not vault_path:
        return {}, ""

    rules_path = vault_path / ".agents" / "REGLAS_GLOBALES.md"
    if not rules_path.exists():
        return {}, ""

    try:
        content = rules_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Could not read rules file: %s", e)
        return {}, ""

    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return {}, match.group(2).strip()
        return frontmatter, match.group(2).strip()
    except yaml.YAMLError as e:
        logger.warning("Malformed YAML in REGLAS_GLOBALES.md: %s", e)
        return {}, ""


def load_vault_rules(force_reload: bool = False) -> list[dict[str, Any]]:
    """Load validations from vault rules frontmatter. Cached in memory."""
    global _rules_cache  # pylint: disable=global-statement
    if _rules_cache is not None and not force_reload:
        return _rules_cache

    frontmatter, _ = _read_rules_file()
    validations = frontmatter.get("validations", [])
    _rules_cache = validations if isinstance(validations, list) else []
    return _rules_cache


def load_vault_rules_prose(force_reload: bool = False) -> str:
    """Load the prose body of REGLAS_GLOBALES.md (without frontmatter). Cached."""
    global _prose_cache  # pylint: disable=global-statement
    if _prose_cache is not None and not force_reload:
        return _prose_cache

    _, prose = _read_rules_file()
    _prose_cache = prose
    return _prose_cache


def invalidate_rules_cache() -> None:
    """Invalidate both caches. Called when REGLAS_GLOBALES.md is edited."""
    global _rules_cache, _prose_cache  # pylint: disable=global-statement
    _rules_cache = None
    _prose_cache = None
