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

import logging
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)

# Default excluded folders for vault scans
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


class VaultProfileConfig(BaseModel):
    """Optional user/vault profile configuration."""

    name: Optional[str] = Field(default=None, description="Profile identifier")
    prompt_sets: list[str] = Field(
        default_factory=list,
        description="Enabled prompt sets or individual profile prompts",
    )
    tool_sets: list[str] = Field(
        default_factory=list,
        description="Enabled optional MCP tool sets",
    )
    standards: dict[str, str] = Field(
        default_factory=dict,
        description="Named standard documents exposed as MCP resources",
    )
    local_docs: dict[str, str] = Field(
        default_factory=dict,
        description="Named local documentation notes for this profile",
    )
    integrations: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Named external integrations declared by this profile",
    )


def nfc(text: str) -> str:
    """Return ``text`` in Unicode NFC form."""
    return unicodedata.normalize("NFC", text)


class TemplateSpec(BaseModel):
    """Default template and folder for one note type."""

    template: str = Field(description="Template file inside templates_folder")
    folder: str = Field(default="", description="Default (base) folder for the type")
    choose_subfolder: bool = Field(
        default=False,
        description="The folder is organised by topic/project: a subfolder must be chosen",
    )


class VaultTaxonomy(BaseModel):
    """
    Declarative description of how this vault is organised.

    Lets tools and skills ask *where* things live instead of hardcoding
    folder names, so the same skill works across vaults with different
    layouts. Every field is optional: when absent, callers fall back to
    their previous heuristics.
    """

    roles: dict[str, str] = Field(
        default_factory=dict,
        description="Semantic role to folder, e.g. {'inbox': '00_Bandeja'}",
    )
    types: list[str] = Field(
        default_factory=list,
        description="Valid frontmatter 'type' values for this vault",
    )
    templates: dict[str, TemplateSpec] = Field(
        default_factory=dict,
        description="Note type to default template and folder",
    )

    @field_validator("types", mode="before")
    @classmethod
    def _normalise_types(cls, value: Any) -> Any:
        """NFC-normalise type names (macOS file names and YAML may use NFD).

        An empty ``types:`` key parses as None; treat it as no list instead of
        invalidating the whole VaultConfig (and with it private_paths).
        """
        if value is None:
            return []
        if isinstance(value, list):
            return [nfc(v) if isinstance(v, str) else v for v in value]
        return value

    @field_validator("templates", mode="before")
    @classmethod
    def _tolerant_templates(cls, value: Any) -> Any:
        """Accept ``type: Template.md`` shorthand and drop invalid entries.

        One bad entry must not invalidate the whole VaultConfig: that would
        silently drop private_paths and the rest of the vault settings.
        """
        if not isinstance(value, dict):
            if value is not None:
                logger.warning("Ignoring taxonomy.templates: expected a mapping")
            return {}
        clean: dict[str, TemplateSpec] = {}
        for key, spec in value.items():
            if isinstance(spec, str):
                spec = {"template": spec}
            try:
                clean[nfc(str(key))] = TemplateSpec.model_validate(spec)
            except ValidationError as e:
                logger.warning("Ignoring taxonomy.templates.%s: %s", key, e)
        return clean


class VaultConfig(BaseModel):
    """
    Minimal vault configuration schema.

    Only operational settings that tools genuinely need.
    Behavior/style comes from REGLAS_GLOBALES.md and skills.
    """

    version: str = Field(default="1.0", description="Config schema version")
    taxonomy: VaultTaxonomy = Field(
        default_factory=VaultTaxonomy,
        description="Optional declarative description of the vault layout",
    )
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
    profile: VaultProfileConfig = Field(
        default_factory=VaultProfileConfig,
        description="Optional vault-specific profile configuration",
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
            logger.warning("Ignoring %s: top level is not a mapping", config_path)
            return None

        return VaultConfig(**data)

    except (OSError, ValueError, yaml.YAMLError) as e:
        # Loud on purpose: an invalid vault.yaml silently disables taxonomy
        # (type validation included), templates_folder and private_paths.
        logger.warning("Ignoring invalid %s: %s", config_path, e)
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
    """Invalidate the vault config cache and what is derived from it."""
    _load_vault_config_cached.cache_clear()
    # private_paths feed the protection patterns: drop that cache too.
    # pylint: disable-next=import-outside-toplevel
    from .utils.security import invalidate_forbidden_patterns_cache

    invalidate_forbidden_patterns_cache()


def resolve_role(vault_path: Path, role: str) -> Optional[Path]:
    """
    Resolve a semantic role to an existing folder in this vault.

    Args:
        vault_path: Path to the Obsidian vault
        role: Role name declared under taxonomy.roles, e.g. "inbox"

    Returns:
        The folder Path if declared and it exists, None otherwise.
    """
    config = get_vault_config(vault_path)
    if not config:
        return None

    folder = config.taxonomy.roles.get(role)
    if not folder:
        return None

    candidate = vault_path / folder
    return candidate if candidate.is_dir() else None


def resolve_local_doc(
    vault_path: Path, name: str, fallback_filename: Optional[str] = None
) -> Optional[Path]:
    """
    Resolve a named local document declared under profile.local_docs.

    Falls back to searching the vault by filename so a stale or missing
    config entry degrades to a search instead of silently reading nothing.

    Args:
        vault_path: Path to the Obsidian vault
        name: Key under profile.local_docs, e.g. "tag_registry"
        fallback_filename: Filename to search for when the config misses

    Returns:
        The document Path if found, None otherwise.
    """
    # Local import avoids a module-level cycle: security loads vault config.
    from .utils.security import (  # pylint: disable=import-outside-toplevel,cyclic-import
        iter_safe_vault_files,
        resolve_vault_path,
    )

    config = get_vault_config(vault_path)
    if config:
        declared = config.profile.local_docs.get(name)
        if declared:
            candidate, _ = resolve_vault_path(
                declared, vault_path, "read configured document"
            )
            if candidate and candidate.is_file():
                return candidate

    if not fallback_filename:
        return None

    return next(iter_safe_vault_files(vault_path, fallback_filename), None)
