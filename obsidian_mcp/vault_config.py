"""
Minimal vault configuration loader.

This module provides a simple way to load optional vault-specific settings
from .agents/vault.yaml. The schema is intentionally minimal - behavior
and style should come from REGLAS_GLOBALES.md and skills, not from config.

Usage:
    from ..vault_config import get_vault_config
    config = get_vault_config(vault_path)
    if config and config.templates_folder:
        templates_path = vault_path / config.templates_folder
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

# Default excluded folders for semantic search
DEFAULT_EXCLUDED_FOLDERS: tuple[str, ...] = (
    "00_Sistema",
    "ZZ_Plantillas",
    "04_Recursos/Obsidian",
    ".agents",
    ".trash",
    ".git",
    ".obsidian",
    ".gemini",
    ".space",
    ".makemd",
    ".obsidianrag",
)

# Default excluded file patterns (regex)
DEFAULT_EXCLUDED_PATTERNS: tuple[str, ...] = (
    r".*MOC\.md",
    r".*Home\.md",
    r".*Inbox\.md",
    r".*Panel.*\.md",
    r".*\.agent\.md",
    r"copilot-instructions\.md",
)


class VaultConfig(BaseModel):
    """
    Minimal vault configuration schema.

    Only operational settings that tools genuinely need.
    Behavior/style comes from REGLAS_GLOBALES.md and skills.
    """

    version: str = Field(default="1.0", description="Config schema version")
    templates_folder: Optional[str] = Field(
        default=None, description="Folder containing note templates"
    )
    private_paths: list[str] = Field(
        default_factory=list, description="Glob patterns for private/restricted paths"
    )
    excluded_folders: list[str] = Field(
        default_factory=lambda: list(DEFAULT_EXCLUDED_FOLDERS),
        description="List of folder names to exclude from search",
    )
    excluded_patterns: list[str] = Field(
        default_factory=lambda: list(DEFAULT_EXCLUDED_PATTERNS),
        description="Regex patterns for files to exclude from search",
    )


@lru_cache(maxsize=1)
def _load_vault_config_cached(vault_path_str: str) -> Optional[VaultConfig]:
    """Load and cache vault configuration."""
    vault_path = Path(vault_path_str)
    config_path = vault_path / ".agents" / "vault.yaml"

    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            return None

        return VaultConfig(**data)

    except (OSError, ValueError, yaml.YAMLError):
        return None


def get_vault_config(vault_path: Path) -> Optional[VaultConfig]:
    """
    Get vault configuration from .agents/vault.yaml if it exists.

    Args:
        vault_path: Path to the Obsidian vault

    Returns:
        VaultConfig if configuration exists and is valid, None otherwise.
    """
    return _load_vault_config_cached(str(vault_path))


def invalidate_vault_config_cache() -> None:
    """Invalidate the vault config cache."""
    _load_vault_config_cached.cache_clear()
