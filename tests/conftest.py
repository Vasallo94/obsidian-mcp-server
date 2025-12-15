"""
Configuración y fixtures para los tests de Obsidian MCP Server
"""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Agregar el directorio raíz al path para importar el módulo
sys.path.insert(0, str(Path(__file__).parent.parent))

# Cargar variables de entorno para los tests
load_dotenv()


@pytest.fixture
def vault_path():
    """Fixture que proporciona el path del vault de Obsidian"""
    path = os.getenv("OBSIDIAN_VAULT_PATH")
    if not path:
        pytest.skip("OBSIDIAN_VAULT_PATH no está configurado")
    return Path(path)


@pytest.fixture
def sample_vault_content(vault_path):
    """Fixture que verifica que hay contenido en el vault"""
    if not vault_path.exists():
        pytest.skip(f"El vault no existe en {vault_path}")

    md_files = list(vault_path.rglob("*.md"))
    if not md_files:
        pytest.skip("No hay archivos markdown en el vault")

    return md_files
