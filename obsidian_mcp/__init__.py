"""
Servidor MCP para Obsidian - Gestión avanzada de tu vault
Permite interactuar con tu vault de Obsidian desde Claude u otros clientes MCP

Estructura modular:
- config: Configuración y variables de entorno
- server: Servidor MCP principal
- tools: Herramientas organizadas por categoría (navegación, creación, análisis)
- resources: Recursos MCP del vault
- prompts: Prompts especializados
- utils: Utilidades compartidas
"""

from .config import APP_NAME, APP_VERSION, get_vault_path, validate_configuration
from .server import create_server, main, run_server

__version__ = APP_VERSION
__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "create_server",
    "get_vault_path",
    "main",
    "run_server",
    "validate_configuration",
]
