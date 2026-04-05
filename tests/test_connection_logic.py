"""
Tests for the connection logic in SemanticService.

These tests verify the vectorized similarity and filtering logic.
Uses pytest with proper fixtures to avoid polluting sys.modules.
"""

import importlib.util
import os
from unittest.mock import MagicMock, patch

import pytest

HAS_NUMPY = importlib.util.find_spec("numpy") is not None


class TestSemanticServiceMixin:
    """Expose a small public testing surface for SemanticService internals."""

    def set_mock_db_payload(self, payload: dict[str, object]) -> None:
        """Install a mock DB payload and stub DB initialization."""
        self._db = MagicMock()
        self._db.get.return_value = payload
        self._ensure_db = MagicMock()

    def should_exclude_path(self, note_path: str) -> bool:
        """Proxy exclusion logic through a public test helper."""
        return self._should_exclude(note_path)


@pytest.fixture
def mock_dependencies():
    """Mock all dependencies to isolate SemanticService testing."""
    # We need to mock before importing the module
    mocks = {}
    mock_obj = MagicMock()

    # Mock all langchain submodules that might be imported
    langchain_mocks = {
        "langchain_chroma": mock_obj,
        "langchain_core": mock_obj,
        "langchain_core.documents": mock_obj,
        "langchain_core.prompts": mock_obj,
        "langchain_core.embeddings": mock_obj,
        "langchain_core.runnables": mock_obj,
        "langchain_community": mock_obj,
        "langchain_huggingface": mock_obj,
        "langchain_ollama": mock_obj,
        "langchain_text_splitters": mock_obj,
    }

    with patch.dict("sys.modules", langchain_mocks):
        yield mocks


@pytest.fixture
def mock_service(mock_dependencies):
    """Create a mock SemanticService for testing."""
    semantic_service_module = pytest.importorskip(
        "obsidian_mcp.semantic.service", exc_type=ImportError
    )
    base_class = semantic_service_module.SemanticService

    class TestSemanticService(TestSemanticServiceMixin, base_class):
        """Concrete test double for SemanticService."""

    return TestSemanticService("/tmp/mock_vault")


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is required for vectorized tests")
class TestConnectionLogic:
    """Tests for suggest_connections vectorized logic."""

    def test_suggest_connections_vectorized(self, mock_service):
        """Test that similar notes are correctly identified."""
        documents = [
            "Content of Note A with enough words to pass the filter. " * 30,
            "Content of Note B with enough words to pass the filter. " * 30,
            "Short note.",
            "MOC content here.",
            "System file content.",
            "Diff content note C. " * 30,
        ]

        embeddings = [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.5, 0.5],
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 1.0],
        ]

        metadatas = [
            {"source": "03_Notas/Note A.md", "links": ""},
            {"source": "03_Notas/Note B.md", "links": ""},
            {"source": "03_Notas/Short.md", "links": ""},
            {"source": "00_Sistema/MyMOC.md", "links": ""},
            {"source": "copilot-instructions.md", "links": ""},
            {"source": "03_Notas/Note C.md", "links": ""},
        ]

        mock_service.set_mock_db_payload(
            {
                "documents": documents,
                "metadatas": metadatas,
                "embeddings": embeddings,
            }
        )

        suggestions = mock_service.suggest_connections(
            min_palabras=10, limit=5, threshold=0.70
        )

        assert len(suggestions) == 1
        assert suggestions[0]["note_a"] == "Note A.md"
        assert suggestions[0]["note_b"] == "Note B.md"
        assert abs(suggestions[0]["similarity"] - 1.0) < 0.00001

    def test_suggest_connections_skips_canonical_mobile_duplicates(self, mock_service):
        """Canonical note and Samsung-import copy should not be suggested."""
        documents = [
            "Canonical skills content with enough words to pass the filter. " * 30,
            "Canonical skills content with enough words to pass the filter. " * 30,
            "MCP governance content with enough words to pass the filter. " * 30,
        ]

        embeddings = [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.9, 0.1],
        ]

        metadatas = [
            {
                "source": "02_Aprendizaje/IA/Skills en Claude Code y criterio de uso.md",
                "links": "",
            },
            {
                "source": "02_Aprendizaje/IA/Skills en Claude Code y criterio de uso_SM-S906B_Mar-21-1957-2026_1.md",
                "links": "",
            },
            {
                "source": "02_Aprendizaje/IA/Catalogo corporativo MCP con managed-mcp.json.md",
                "links": "",
            },
        ]

        mock_service.set_mock_db_payload(
            {
                "documents": documents,
                "metadatas": metadatas,
                "embeddings": embeddings,
            }
        )

        suggestions = mock_service.suggest_connections(
            min_palabras=10, limit=5, threshold=0.70
        )

        assert len(suggestions) == 1
        assert suggestions[0]["note_a"] == "Skills en Claude Code y criterio de uso.md"
        assert (
            suggestions[0]["note_b"]
            == "Catalogo corporativo MCP con managed-mcp.json.md"
        )

    def test_exclusion_logic(self, mock_service):
        """Test that system files are properly excluded."""
        p1 = os.path.join(mock_service.vault_path, "00_Sistema/File.md")
        assert mock_service.should_exclude_path(p1) is True

        p4 = os.path.join(mock_service.vault_path, "03_Notas/ValidNote.md")
        assert mock_service.should_exclude_path(p4) is False
