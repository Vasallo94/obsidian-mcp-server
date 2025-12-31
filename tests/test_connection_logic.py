import os
import sys
import unittest
from unittest.mock import MagicMock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# 1. Mock external dependencies
# We keep numpy real because we want to test the vector logic
external_mocks = [
    "dotenv",
    "yaml",
    "langchain_chroma",
    "langchain_core",
    "langchain_core.documents",
    "langchain_huggingface",
    "langchain_ollama",
    "langchain_text_splitters",
    "fastmcp",
    # "tqdm"  # We let tqdm import naturally or use the fallback
]
for mod in external_mocks:
    sys.modules[mod] = MagicMock()

# 2. Mock internal modules
internal_mocks = [
    "obsidian_mcp.config",
    # "obsidian_mcp.utils", # Allow utils package
    "obsidian_mcp.utils.logging",
    "obsidian_mcp.utils.vault",
    "obsidian_mcp.utils.mcp_ignore",
    "obsidian_mcp.semantic.indexer",
    "obsidian_mcp.semantic.retriever",
    "obsidian_mcp.server",
    "obsidian_mcp.resources",
]
for mod in internal_mocks:
    sys.modules[mod] = MagicMock()

from obsidian_mcp.semantic.service import SemanticService


class TestConnectionLogic(unittest.TestCase):
    def setUp(self):
        self.service = SemanticService("/tmp/mock_vault")
        self.service._db = MagicMock()
        self.service._ensure_db = MagicMock()

    def test_suggest_connections_vectorized(self):
        # Setup mock data with known embeddings
        # Note A and Note B are identical vectors -> max similarity (1.0)
        # Short note is short
        # Excluded items have vectors too

        # Dimensions: 2D for simplicity
        # A: [1, 0]
        # B: [1, 0] (Same direction)
        # C: [0, 1] (Orthogonal)

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

        self.service._db.get.return_value = {
            "documents": documents,
            "metadatas": metadatas,
            "embeddings": embeddings,
        }

        # Test 1: Default filters, high threshold
        # Should find A <-> B (sim 1.0)
        # Should NOT find A <-> C (sim 0.0)
        suggestions = self.service.suggest_connections(
            min_palabras=10, limit=5, threshold=0.9
        )

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["note_a"], "Note A.md")
        self.assertEqual(suggestions[0]["note_b"], "Note B.md")
        self.assertAlmostEqual(suggestions[0]["similarity"], 1.0, places=5)

    def test_exclusion_logic(self):
        # Reuse existing logic test
        p1 = os.path.join(self.service.vault_path, "00_Sistema/File.md")
        self.assertTrue(self.service._should_exclude(p1))

        p4 = os.path.join(self.service.vault_path, "03_Notas/ValidNote.md")
        self.assertFalse(self.service._should_exclude(p4))


if __name__ == "__main__":
    unittest.main()
