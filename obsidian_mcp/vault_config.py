"""
Minimal vault configuration loader.

This module provides a simple way to load optional vault-specific settings
from .agent/vault.yaml. The schema is intentionally minimal - behavior
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
        default_factory=list, description="List of folder names to exclude from search"
    )


@lru_cache(maxsize=1)
def _load_vault_config_cached(vault_path_str: str) -> Optional[VaultConfig]:
    """Load and cache vault configuration."""
    vault_path = Path(vault_path_str)
    config_path = vault_path / ".agent" / "vault.yaml"

    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            return None

        return VaultConfig(**data)

    except Exception:
        return None


def get_vault_config(vault_path: Path) -> Optional[VaultConfig]:
    """
    Get vault configuration from .agent/vault.yaml if it exists.

    Args:
        vault_path: Path to the Obsidian vault

    Returns:
        VaultConfig if configuration exists and is valid, None otherwise.
    """
    return _load_vault_config_cached(str(vault_path))


def invalidate_vault_config_cache() -> None:
    """Invalidate the vault config cache."""
    _load_vault_config_cached.cache_clear()
