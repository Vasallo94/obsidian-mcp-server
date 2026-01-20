"""
Tests for the connection logic in SemanticService.

These tests verify the vectorized similarity and filtering logic.
Uses pytest with proper fixtures to avoid polluting sys.modules.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# Check if numpy is available (required for vectorized tests)
try:
    import numpy  # noqa: F401 # type: ignore

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


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
    try:
        from obsidian_mcp.semantic.service import SemanticService

        service = SemanticService("/tmp/mock_vault")
        service._db = MagicMock()
        service._ensure_db = MagicMock()
        return service
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"SemanticService dependencies not available: {e}")


@pytest.mark.skipif(not HAS_NUMPY, reason="numpy is required for vectorized tests")
class TestConnectionLogic:
    """Tests for suggest_connections vectorized logic."""

    def test_suggest_connections_vectorized(self, mock_service):
        """Test that similar notes are correctly identified."""
        # Setup mock data with known embeddings
        # Note A and Note B are identical vectors -> max similarity (1.0)

        documents = [
            "Content of Note A with enough words to pass the filter. " * 30,  # 0
            "Content of Note B with enough words to pass the filter. " * 30,  # 1
            "Short note.",  # 2
            "MOC content here.",  # 3
            "System file content.",  # 4
            "Diff content note C. " * 30,  # 5
        ]

        embeddings = [
            [1.0, 0.0],  # A
            [1.0, 0.0],  # B (Matches A)
            [0.5, 0.5],  # Short
            [0.0, 0.0],  # MOC
            [0.0, 0.0],  # System
            [0.0, 1.0],  # C (Diff)
        ]

        metadatas = [
            {"source": "03_Notas/Note A.md", "links": ""},
            {"source": "03_Notas/Note B.md", "links": ""},
            {"source": "03_Notas/Short.md", "links": ""},
            {"source": "00_Sistema/MyMOC.md", "links": ""},
            {"source": "copilot-instructions.md", "links": ""},
            {"source": "03_Notas/Note C.md", "links": ""},
        ]

        mock_service._db.get.return_value = {
            "documents": documents,
            "metadatas": metadatas,
            "embeddings": embeddings,
        }

        suggestions = mock_service.suggest_connections(
            min_palabras=10, limit=5, threshold=0.70
        )

        assert len(suggestions) == 1
        assert suggestions[0]["note_a"] == "Note A.md"
        assert suggestions[0]["note_b"] == "Note B.md"
        assert abs(suggestions[0]["similarity"] - 1.0) < 0.00001

    def test_exclusion_logic(self, mock_service):
        """Test that system files are properly excluded."""
        p1 = os.path.join(mock_service.vault_path, "00_Sistema/File.md")
        assert mock_service._should_exclude(p1) is True

        p4 = os.path.join(mock_service.vault_path, "03_Notas/ValidNote.md")
        assert mock_service._should_exclude(p4) is False
