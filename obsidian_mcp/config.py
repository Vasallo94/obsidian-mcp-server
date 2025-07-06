"""
Configuración centralizada y gestión de variables de entorno.

Este módulo carga la configuración desde un archivo .env y proporciona
funciones para acceder a las variables de configuración de forma segura
y validarlas al inicio de la aplicación.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- Constantes de la Aplicación ---
APP_NAME: str = "obsidian-mcp"
APP_VERSION: str = "1.0.0"
PROMPT_LIBRARY_DIR: str = "Prompt Library"

# --- Acceso a la Configuración ---


def get_vault_path() -> Optional[Path]:
    """
    Obtiene la ruta al vault de Obsidian desde las variables de entorno.

    Returns:
        Un objeto Path si la variable está definida, de lo contrario None.
    """
    path_str = os.getenv("OBSIDIAN_VAULT_PATH")
    return Path(path_str) if path_str else None


# --- Validación de la Configuración ---


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
        return False, "La variable de entorno OBSIDIAN_VAULT_PATH no está definida."
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

    Actualmente, solo valida la ruta del vault.

    Returns:
        Una tupla con un booleano (éxito) y un mensaje de error (si falla).
    """
    vault_path = get_vault_path()
    return validate_vault_path(vault_path)
