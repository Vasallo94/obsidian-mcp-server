"""
Configuración y fixtures para los tests de Obsidian MCP Server
"""

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
def vault_path(isolated_vault: Path) -> Path:
    """Return the generated test vault."""
    return isolated_vault


@pytest.fixture
def sample_vault_content(vault_path: Path) -> list[Path]:
    """Return Markdown files from the generated test vault."""
    return list(vault_path.rglob("*.md"))
