"""
Configuración del servidor MCP para Obsidian
Maneja variables de entorno y configuración global
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración del vault de Obsidian
OBSIDIAN_VAULT_PATH: str = os.getenv('OBSIDIAN_VAULT_PATH', '')

def validate_configuration() -> tuple[bool, str]:
    """
    Valida la configuración del servidor
    
    Returns:
        Tupla (es_válida, mensaje_error)
    """
    if not OBSIDIAN_VAULT_PATH:
        return False, "❌ Variable de entorno OBSIDIAN_VAULT_PATH no configurada"
    
    vault_path = Path(OBSIDIAN_VAULT_PATH)
    if not vault_path.exists():
        return False, f"❌ El vault no existe en {OBSIDIAN_VAULT_PATH}"
    
    if not vault_path.is_dir():
        return False, f"❌ {OBSIDIAN_VAULT_PATH} no es un directorio"
    
    return True, "✅ Configuración válida"

def get_vault_path() -> Path:
    """
    Obtiene el Path del vault de Obsidian
    
    Returns:
        Path del vault
        
    Raises:
        ValueError: Si la configuración no es válida
    """
    is_valid, error_message = validate_configuration()
    if not is_valid:
        raise ValueError(error_message)
    
    return Path(OBSIDIAN_VAULT_PATH)

# Configuración de la aplicación
APP_NAME = "Obsidian MCP Server"
APP_VERSION = "2.0.0"

# Configuración por defecto del servidor
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_TRANSPORT = "stdio"
