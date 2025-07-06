"""
Configuración de logging para el servidor MCP
"""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO, logger_name: Optional[str] = None
) -> logging.Logger:
    """
    Configura el logging para el servidor MCP

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
    Obtiene un logger con el nombre especificado

    Args:
        name: Nombre del logger

    Returns:
        Logger configurado
    """
    return setup_logging(logger_name=name)
