"""
Configuración y fixtures para los tests de Obsidian MCP Server
"""

import os
import sys
from pathlib import Path

import pytest

# Agregar el directorio raíz al path para importar el módulo
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def isolated_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Keep the default test suite away from a developer's configured vault."""
    vault = tmp_path
    (vault / "sample.md").write_text("# Test note\n", encoding="utf-8")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))

    from obsidian_mcp.config import reset_settings

    reset_settings()
    yield vault
    reset_settings()


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
