"""
Configuración centralizada de logging para el servidor MCP.

Proporciona funciones para obtener loggers consistentes en toda la aplicación.
"""

import logging
import sys
from typing import Optional

# Flag to track if logging has been configured
_LOGGING_CONFIGURED = False


def _get_log_level() -> int:
    """Get log level from configuration (lazy import to avoid circular deps)."""
    try:
        from ..config import get_app_settings  # pylint: disable=import-outside-toplevel

        settings = get_app_settings()
        return getattr(logging, settings.log_level.upper(), logging.INFO)
    except (AttributeError, ImportError):
        return logging.INFO


def configure_logging(level: Optional[int] = None) -> None:
    """
    Configure root logging for the obsidian_mcp package.

    Args:
        level: Optional log level override. If None, uses config setting.
    """
    global _LOGGING_CONFIGURED  # pylint: disable=global-statement
    if _LOGGING_CONFIGURED:
        return

    if level is None:
        level = _get_log_level()

    # Configure root logger for obsidian_mcp
    root_logger = logging.getLogger("obsidian_mcp")
    root_logger.setLevel(level)

    if not root_logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    root_logger.propagate = False
    _LOGGING_CONFIGURED = True


def setup_logging(
    level: int = logging.INFO,
    logger_name: Optional[str] = None,
) -> logging.Logger:
    """
    Configura el logging para el servidor MCP.

    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        logger_name: Nombre del logger (por defecto usa __name__)

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(logger_name or __name__)

    # Solo configurar si no tiene handlers (evitar duplicados)
    if not logger.handlers:
        # Configurar formato
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Handler para stderr
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)

        # Configurar logger
        logger.addHandler(handler)
        logger.setLevel(level)

        # Evitar propagación a root logger
        logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado con el nombre especificado.

    Automatically configures the root obsidian_mcp logger if not yet configured.

    Args:
        name: Nombre del logger (típicamente __name__)

    Returns:
        Logger configurado
    """
    configure_logging()
    return logging.getLogger(name)
