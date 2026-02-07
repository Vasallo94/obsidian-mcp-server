"""
Tests for the Skill Generator functionality.
"""

import pytest

from obsidian_mcp.tools.agents_generator import (
    generate_skill,
    suggest_skills_for_vault,
    sync_skills,
)


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault with .agent structure."""
    vault = tmp_path / "test_vault"
    vault.mkdir()

    # Create .agent/skills directory
    skills_dir = vault / ".agent" / "skills"
    skills_dir.mkdir(parents=True)

    return vault


class TestGenerateSkill:
    """Tests for generate_skill function."""

    def test_generates_skill_successfully(self, temp_vault, monkeypatch):
        """Should create a new skill with correct structure."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.agents_generator.get_vault_path",
            lambda: temp_vault,
        )

        result = generate_skill(
            nombre="test-skill",
            descripcion="Una skill de prueba",
            instrucciones="Sigue estas instrucciones...",
        )

        assert result.success
        assert "test-skill" in result.data

        # Verify file was created
        skill_file = temp_vault / ".agent" / "skills" / "test-skill" / "SKILL.md"
        assert skill_file.exists()

        content = skill_file.read_text()
        assert "name: test-skill" in content
        assert "Una skill de prueba" in content
        assert "REGLAS_GLOBALES" in content
        assert "REGLA DE ORO" in content

    def test_normalizes_skill_name(self, temp_vault, monkeypatch):
        """Should normalize skill names (lowercase, dashes)."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.agents_generator.get_vault_path",
            lambda: temp_vault,
        )

        result = generate_skill(
            nombre="My Test Skill",
            descripcion="Test",
            instrucciones="Test",
        )

        assert result.success
        skill_dir = temp_vault / ".agent" / "skills" / "my-test-skill"
        assert skill_dir.exists()

    def test_fails_if_skill_exists(self, temp_vault, monkeypatch):
        """Should fail if skill already exists."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.agents_generator.get_vault_path",
            lambda: temp_vault,
        )

        # Create existing skill
        existing = temp_vault / ".agent" / "skills" / "existing" / "SKILL.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("# Existing")

        result = generate_skill(
            nombre="existing",
            descripcion="Test",
            instrucciones="Test",
        )

        assert not result.success
        assert "Ya existe" in result.error

    def test_includes_custom_tools(self, temp_vault, monkeypatch):
        """Should include custom tools in frontmatter."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.agents_generator.get_vault_path",
            lambda: temp_vault,
        )

        result = generate_skill(
            nombre="custom-tools",
            descripcion="Test",
            instrucciones="Test",
            herramientas="web, github, sequentialthinking",
        )

        assert result.success
        skill_file = temp_vault / ".agent" / "skills" / "custom-tools" / "SKILL.md"
        content = skill_file.read_text()
        assert "web, github, sequentialthinking" in content


class TestSuggestSkills:
    """Tests for suggest_skills_for_vault function."""

    def test_analyzes_vault_patterns(self, temp_vault, monkeypatch):
        """Should analyze vault and return suggestions."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.agents_generator.get_vault_path",
            lambda: temp_vault,
        )

        # Create some notes with tags
        notes_dir = temp_vault / "02_Aprendizaje" / "Física"
        notes_dir.mkdir(parents=True)

        for i in range(10):
            note = notes_dir / f"nota_{i}.md"
            note.write_text(f"# Nota {i}\n\n#física #ciencia\n\nContenido")

        result = suggest_skills_for_vault()

        assert result.success
        assert "Análisis del Vault" in result.data
        assert "10 notas" in result.data or "física" in result.data.lower()


class TestSyncSkills:
    """Tests for sync_skills function."""

    def test_detects_missing_reglas_globales(self, temp_vault, monkeypatch):
        """Should detect skills missing REGLAS_GLOBALES reference."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.agents_generator.get_vault_path",
            lambda: temp_vault,
        )

        # Create skill without REGLAS_GLOBALES
        skill_dir = temp_vault / ".agent" / "skills" / "incomplete"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Incomplete Skill\n\nNo rules here.")

        result = sync_skills(actualizar=False)

        assert result.success
        assert "incomplete" in result.data
        assert "REGLAS_GLOBALES" in result.data

    def test_fixes_issues_when_actualizar(self, temp_vault, monkeypatch):
        """Should fix issues when actualizar=True."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.agents_generator.get_vault_path",
            lambda: temp_vault,
        )

        # Create skill without golden rule
        skill_dir = temp_vault / ".agent" / "skills" / "fixme"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "# Fixme Skill\n\nTiene REGLAS_GLOBALES pero sin golden rule."
        )

        result = sync_skills(actualizar=True)

        assert result.success
        assert "fixme" in result.data

        # Verify fix was applied
        content = skill_file.read_text()
        assert "REGLA DE ORO" in content

    def test_reports_all_ok(self, temp_vault, monkeypatch):
        """Should report OK if all skills are valid."""
        monkeypatch.setattr(
            "obsidian_mcp.tools.agents_generator.get_vault_path",
            lambda: temp_vault,
        )

        # Create valid skill
        skill_dir = temp_vault / ".agent" / "skills" / "valid"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "# Valid Skill\n\n"
            "Reference to REGLAS_GLOBALES here.\n\n"
            "## REGLA DE ORO DE EDICIÓN\n"
            "Instructions here."
        )

        result = sync_skills()

        assert result.success
        assert "sincronizadas correctamente" in result.data
