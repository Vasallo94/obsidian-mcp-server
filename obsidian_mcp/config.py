"""
Configuración centralizada usando Pydantic Settings.

Este módulo carga la configuración desde variables de entorno y archivos .env,
proporcionando validación tipada y valores por defecto sensatos.
"""

from pathlib import Path
from typing import Optional, Tuple

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class VaultSettings(BaseSettings):
    """
    Environment-level vault configuration.

    NOTE: Vault-specific settings (folder names, exclusions, etc.) are now
    loaded from .agent/vault.yaml within the vault. See vault_config.py.

    This class only contains:
    - vault_path: Required path to the Obsidian vault
    - Performance/operational settings that are server-level, not vault-level
    """

    model_config = SettingsConfigDict(
        env_prefix="OBSIDIAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vault_path: Optional[Path] = Field(
        default=None,
        description="Path to the Obsidian vault",
    )

    # Performance settings (server-level, not vault-specific)
    search_timeout_seconds: int = Field(
        default=180,
        ge=30,
        le=600,
        description="Timeout for semantic search operations",
    )
    max_search_results: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Maximum search results to return",
    )
    cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Cache TTL for note lookups",
    )

    @field_validator("vault_path", mode="before")
    @classmethod
    def validate_vault_path_format(cls, v: Optional[str]) -> Optional[Path]:
        """Convert string to Path if provided."""
        if v is None or v == "":
            return None
        return Path(v)


class AppSettings(BaseSettings):
    """Application-wide settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="obsidian-mcp")
    app_version: str = Field(default="1.0.0")
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    prompt_library_dir: str = Field(default="Prompt Library")


# Singleton instances for caching
_vault_settings: Optional[VaultSettings] = None
_app_settings: Optional[AppSettings] = None


def get_vault_settings() -> VaultSettings:
    """Get or create VaultSettings singleton."""
    global _vault_settings
    if _vault_settings is None:
        _vault_settings = VaultSettings()
    return _vault_settings


def get_app_settings() -> AppSettings:
    """Get or create AppSettings singleton."""
    global _app_settings
    if _app_settings is None:
        _app_settings = AppSettings()
    return _app_settings


def reset_settings() -> None:
    """Reset settings singletons (useful for testing)."""
    global _vault_settings, _app_settings
    _vault_settings = None
    _app_settings = None


# --- Backward Compatibility Layer ---
# These maintain compatibility with existing code

# Constants (now derived from settings)
APP_NAME: str = "obsidian-mcp"
APP_VERSION: str = "1.0.0"
PROMPT_LIBRARY_DIR: str = "Prompt Library"


def get_vault_path() -> Optional[Path]:
    """
    Obtiene la ruta al vault de Obsidian desde la configuración.

    Returns:
        Un objeto Path si está definido, de lo contrario None.
    """
    return get_vault_settings().vault_path


def validate_vault_path(vault_path: Optional[Path]) -> Tuple[bool, str]:
    """
    Valida que la ruta del vault de Obsidian sea válida.

    Args:
        vault_path: La ruta al vault a validar.

    Returns:
        Una tupla con un booleano indicando si la validación fue exitosa
        y un mensaje de error si no lo fue.
    """
    if not vault_path:
        return (
            False,
            "La variable de entorno OBSIDIAN_VAULT_PATH no está definida.",
        )
    if not vault_path.exists():
        return (
            False,
            f"La ruta del vault especificada no existe: {vault_path}",
        )
    if not vault_path.is_dir():
        return (
            False,
            f"La ruta del vault especificada no es un directorio: {vault_path}",
        )
    return True, ""


def validate_configuration() -> Tuple[bool, str]:
    """
    Valida toda la configuración de la aplicación.

    Returns:
        Una tupla con un booleano (éxito) y un mensaje de error (si falla).
    """
    vault_path = get_vault_path()
    return validate_vault_path(vault_path)
