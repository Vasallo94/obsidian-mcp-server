"""
Centralized messages for MCP tools.

This module provides consistent error and success messages across all tools.
Messages are designed to be user-friendly and parseable by LLM agents.

Note: Error/success indicators are added by the tool functions, not here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorMessages:
    """Standardized error messages for MCP tools."""

    # Configuration errors
    VAULT_NOT_CONFIGURED: str = "La ruta del vault no esta configurada."
    VAULT_NOT_EXISTS: str = "La ruta del vault especificada no existe: {path}"
    VAULT_NOT_DIRECTORY: str = "La ruta del vault no es un directorio: {path}"

    # File operation errors
    FILE_NOT_FOUND: str = "Archivo no encontrado: {path}"
    FILE_ALREADY_EXISTS: str = "El archivo ya existe: {path}"
    FILE_READ_ERROR: str = "Error leyendo el archivo: {path}"
    FILE_WRITE_ERROR: str = "Error escribiendo el archivo: {path}"

    # Access errors
    ACCESS_DENIED: str = "Acceso denegado: {path}"
    PATH_OUTSIDE_VAULT: str = "La ruta esta fuera del vault: {path}"
    RESTRICTED_FOLDER: str = "Carpeta restringida: {path}"

    # Validation errors
    INVALID_PARAMETER: str = "Parametro invalido: {param}"
    REQUIRED_PARAMETER: str = "Parametro requerido: {param}"
    INVALID_FRONTMATTER: str = "Frontmatter YAML invalido: {error}"

    # Operation errors
    DELETE_REQUIRES_CONFIRM: str = "Eliminacion requiere confirmacion explícita."
    SEMANTIC_NOT_AVAILABLE: str = "Servicio semantico no disponible."
    TIMEOUT: str = "Operacion excedio el tiempo limite ({seconds}s)."


@dataclass(frozen=True)
class SuccessMessages:
    """Standardized success messages for MCP tools."""

    # Note operations
    NOTE_CREATED: str = "Nota creada: {path}"
    NOTE_UPDATED: str = "Nota actualizada: {path}"
    NOTE_DELETED: str = "Nota eliminada: {path}"
    NOTE_MOVED: str = "Nota movida de {source} a {destination}"

    # Content operations
    CONTENT_APPENDED: str = "Contenido agregado a: {path}"
    SEARCH_COMPLETED: str = "Busqueda completada: {count} resultados"

    # Index operations
    INDEX_UPDATED: str = "Indice actualizado"
    INDEX_STATS: str = (
        "Indice actualizado:\\n"
        "- Notas procesadas: {docs_processed}\\n"
        "- Nuevas: {docs_new}\\n"
        "- Modificadas: {docs_modified}\\n"
        "- Tiempo: {time_seconds:.1f}s"
    )


# Singleton instances
ERRORS = ErrorMessages()
SUCCESS = SuccessMessages()


def format_error(message: str, **kwargs: str) -> str:
    """Format an error message with optional parameters.

    Args:
        message: The error message template.
        **kwargs: Values to substitute in the template.

    Returns:
        Formatted error message with error indicator.
    """
    formatted = message.format(**kwargs) if kwargs else message
    return f"Error: {formatted}"


def format_success(message: str, **kwargs: object) -> str:
    """Format a success message with optional parameters.

    Args:
        message: The success message template.
        **kwargs: Values to substitute in the template.

    Returns:
        Formatted success message with success indicator.
    """
    formatted = message.format(**kwargs) if kwargs else message
    return f"OK: {formatted}"
