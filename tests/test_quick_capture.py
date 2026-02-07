"""
Tests for Quick Capture and Smart Append functionality.
"""

import pytest

from obsidian_mcp.tools.creation_logic import append_to_section, quick_capture


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault for testing."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    return vault


class TestQuickCapture:
    """Tests for quick_capture function."""

    def test_quick_capture_creates_note_in_inbox(self, temp_vault, monkeypatch):
        """Should create a note in the Inbox folder."""
        inbox = temp_vault / "00_Bandeja"
        inbox.mkdir()

        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.get_vault_path",
            lambda: temp_vault,
        )

        result = quick_capture("Esta es una idea rápida")

        assert result.success
        assert "00_Bandeja" in result.data
        assert "Captura" in result.data

        files = list(inbox.glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "Esta es una idea rápida" in content

    def test_quick_capture_with_tags(self, temp_vault, monkeypatch):
        """Should include tags in the created note."""
        inbox = temp_vault / "00_Bandeja"
        inbox.mkdir()

        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.get_vault_path",
            lambda: temp_vault,
        )

        result = quick_capture("Idea con tags", etiquetas="idea, urgente")

        assert result.success

        files = list(inbox.glob("*.md"))
        content = files[0].read_text()
        assert "idea" in content or "urgente" in content

    def test_quick_capture_fallback_to_root(self, temp_vault, monkeypatch):
        """Should create in root if no inbox folder found."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.get_vault_path",
            lambda: temp_vault,
        )

        result = quick_capture("Sin inbox")

        assert result.success
        files = list(temp_vault.glob("*.md"))
        assert len(files) >= 1


class TestAppendToSection:
    """Tests for append_to_section function."""

    def test_append_to_existing_section(self, temp_vault, monkeypatch):
        """Should append content to an existing section."""
        note_path = temp_vault / "test_note.md"
        # Use dedent to avoid leading whitespace issues
        content = (
            "# Test Note\n\n"
            "## Recursos\n\n- Recurso 1\n\n"
            "## Otra Sección\n\nContenido aquí.\n"
        )
        note_path.write_text(content)

        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.get_vault_path",
            lambda: temp_vault,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.find_note_by_name",
            lambda name: note_path,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.check_path_access",
            lambda path, vault, op: (True, None),
        )

        result = append_to_section("test_note.md", "Recursos", "- Recurso nuevo")

        assert result.success
        content = note_path.read_text()
        assert "- Recurso nuevo" in content
        recursos_pos = content.find("## Recursos")
        otra_pos = content.find("## Otra Sección")
        nuevo_pos = content.find("- Recurso nuevo")
        assert recursos_pos < nuevo_pos < otra_pos

    def test_append_creates_section_if_not_exists(self, temp_vault, monkeypatch):
        """Should create section if crear_si_no_existe is True."""
        note_path = temp_vault / "test_note.md"
        note_path.write_text("# Test Note\n\nContenido inicial.\n")

        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.get_vault_path",
            lambda: temp_vault,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.find_note_by_name",
            lambda name: note_path,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.check_path_access",
            lambda path, vault, op: (True, None),
        )

        result = append_to_section(
            "test_note.md", "Nueva Sección", "Contenido nuevo", crear_si_no_existe=True
        )

        assert result.success
        content = note_path.read_text()
        assert "## Nueva Sección" in content
        assert "Contenido nuevo" in content

    def test_append_fails_if_section_not_found_and_no_create(
        self, temp_vault, monkeypatch
    ):
        """Should fail if section not found and crear_si_no_existe is False."""
        note_path = temp_vault / "test_note.md"
        note_path.write_text("# Test Note\n\nContenido.")

        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.get_vault_path",
            lambda: temp_vault,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.find_note_by_name",
            lambda name: note_path,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.check_path_access",
            lambda path, vault, op: (True, None),
        )

        result = append_to_section(
            "test_note.md", "Inexistente", "Algo", crear_si_no_existe=False
        )

        assert not result.success
        assert "No se encontró la sección" in result.error

    def test_append_handles_different_heading_levels(self, temp_vault, monkeypatch):
        """Should find sections regardless of heading level."""
        note_path = temp_vault / "test_note.md"
        content = (
            "# Test Note\n\n"
            "### Subsección\n\nContenido original.\n\n"
            "### Otra Subsección\n\nMás contenido.\n"
        )
        note_path.write_text(content)

        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.get_vault_path",
            lambda: temp_vault,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.find_note_by_name",
            lambda name: note_path,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.check_path_access",
            lambda path, vault, op: (True, None),
        )

        result = append_to_section("test_note.md", "Subsección", "Nuevo contenido")

        assert result.success
        content = note_path.read_text()
        assert "Nuevo contenido" in content
        sub_pos = content.find("### Subsección")
        otra_pos = content.find("### Otra Subsección")
        nuevo_pos = content.find("Nuevo contenido")
        assert sub_pos < nuevo_pos < otra_pos

    def test_append_to_last_section(self, temp_vault, monkeypatch):
        """Should append at end if section is the last one."""
        note_path = temp_vault / "test_note.md"
        content = (
            "# Test Note\n\n"
            "## Primera\n\nContenido.\n\n"
            "## Última\n\nFinal del archivo.\n"
        )
        note_path.write_text(content)

        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.get_vault_path",
            lambda: temp_vault,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.find_note_by_name",
            lambda name: note_path,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.check_path_access",
            lambda path, vault, op: (True, None),
        )

        result = append_to_section("test_note.md", "Última", "Añadido al final")

        assert result.success
        content = note_path.read_text()
        assert "Añadido al final" in content
        final_pos = content.find("Final del archivo.")
        nuevo_pos = content.find("Añadido al final")
        assert final_pos < nuevo_pos

    def test_append_note_not_found(self, temp_vault, monkeypatch):
        """Should fail if note doesn't exist."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.get_vault_path",
            lambda: temp_vault,
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.find_note_by_name",
            lambda name: None,
        )

        result = append_to_section("inexistente.md", "Sección", "Contenido")

        assert not result.success
        assert "No se encontró la nota" in result.error
