"""Regression tests from AFP dogfooding reports."""

import asyncio
from types import SimpleNamespace

import pytest
import yaml

from obsidian_mcp.config import reset_settings
from obsidian_mcp.server import create_server
from obsidian_mcp.tools.analysis_logic import sync_tag_registry
from obsidian_mcp.tools.creation_logic import (
    search_and_replace_global,
    update_frontmatter_logic,
)
from obsidian_mcp.tools.graph_logic import get_local_graph
from obsidian_mcp.utils import invalidate_note_cache
from obsidian_mcp.vault_config import invalidate_vault_config_cache


@pytest.fixture(autouse=True)
def _reset_global_state_after_test():
    yield
    reset_settings()
    invalidate_note_cache()
    invalidate_vault_config_cache()


def _set_vault(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    monkeypatch.setenv(
        "OBSIDIAN_MCP_TOOL_SETS",
        "notes_write,vault_analysis,secundo_selebro",
    )
    reset_settings()
    invalidate_note_cache()
    return vault


class _AcceptCtx:
    async def elicit(self, *args, **kwargs):
        return SimpleNamespace(action="accept")


def test_preview_replace_points_agents_to_apply_replace(tmp_path, monkeypatch):
    vault = _set_vault(monkeypatch, tmp_path)
    note = vault / "note.md"
    note.write_text("before target after", encoding="utf-8")

    result = search_and_replace_global("target", "replacement", solo_preview=True)

    assert result.success
    assert "notes.apply_replace" in result.data
    assert "solo_preview=False" not in result.data


def test_update_frontmatter_rejects_json_that_is_not_an_object(tmp_path, monkeypatch):
    vault = _set_vault(monkeypatch, tmp_path)
    note = vault / "note.md"
    note.write_text("---\ntitle: Test\n---\n\nBody\n", encoding="utf-8")

    result = update_frontmatter_logic("note.md", '["not", "an", "object"]')

    assert not result.success
    assert "objeto JSON" in result.error
    assert note.read_text(encoding="utf-8") == "---\ntitle: Test\n---\n\nBody\n"


def test_update_frontmatter_tool_returns_validation_error_for_non_object_json(
    tmp_path, monkeypatch
):
    vault = _set_vault(monkeypatch, tmp_path)
    rules_dir = vault / ".agents"
    rules_dir.mkdir()
    (rules_dir / "REGLAS_GLOBALES.md").write_text(
        "---\n"
        "validations:\n"
        "  - id: status-values\n"
        "    scope: frontmatter\n"
        "    applies_to: [edit]\n"
        "    field: status\n"
        "    allowed_values: [en_proceso]\n"
        '    warning: "status inválido: {value}"\n'
        "---\n"
        "\n"
        "# Reglas\n",
        encoding="utf-8",
    )
    note = vault / "note.md"
    note.write_text("---\ntitle: Test\n---\n\nBody\n", encoding="utf-8")
    mcp = create_server()
    update_tool = asyncio.run(mcp.get_tool("notes.update_frontmatter"))

    result = update_tool.fn("note.md", '["not", "an", "object"]')

    assert "objeto JSON" in result
    assert "dictionary update sequence" not in result
    assert "'list' object has no attribute" not in result


def test_notes_append_accepts_append_as_end_alias(tmp_path, monkeypatch):
    vault = _set_vault(monkeypatch, tmp_path)
    note = vault / "note.md"
    note.write_text("# Note\n\nOriginal\n", encoding="utf-8")
    mcp = create_server()
    append_tool = asyncio.run(mcp.get_tool("notes.append"))

    result = append_tool.fn("note.md", "Added", position="append")

    assert result.startswith("OK")
    content = note.read_text(encoding="utf-8")
    assert content.index("Added") > content.index("Original")


def test_local_graph_accepts_vault_relative_paths(tmp_path, monkeypatch):
    vault = _set_vault(monkeypatch, tmp_path)
    folder = vault / "Projects" / "AFP"
    folder.mkdir(parents=True)
    note = folder / "Agent Feedback Protocol.md"
    note.write_text("# Agent Feedback Protocol\n\n[[Neighbor]]\n", encoding="utf-8")
    (vault / "Neighbor.md").write_text(
        "[[Agent Feedback Protocol]]\n", encoding="utf-8"
    )

    result = get_local_graph("Projects/AFP/Agent Feedback Protocol.md")

    assert result.success
    assert "Neighbor" in result.data


def test_notes_delete_requires_explicit_confirm_argument(tmp_path, monkeypatch):
    vault = _set_vault(monkeypatch, tmp_path)
    note = vault / "scratch.md"
    note.write_text("temporary", encoding="utf-8")
    mcp = create_server()
    delete_tool = asyncio.run(mcp.get_tool("notes.delete"))
    ctx = SimpleNamespace(elicit=lambda *args, **kwargs: None)

    assert delete_tool.parameters["properties"]["confirm"]["default"] is False
    result = asyncio.run(delete_tool.fn("scratch.md", ctx, confirm=False))

    assert "confirm" in result.lower()
    assert note.exists()


def test_inbox_capture_creates_valid_current_frontmatter(tmp_path, monkeypatch):
    vault = _set_vault(monkeypatch, tmp_path)
    inbox = vault / "00_Bandeja"
    inbox.mkdir()
    rules_dir = vault / ".agents"
    rules_dir.mkdir()
    (rules_dir / "REGLAS_GLOBALES.md").write_text(
        "---\n"
        "validations:\n"
        "  - id: required_frontmatter\n"
        "    applies_to: [create]\n"
        "    scope: frontmatter\n"
        "    required_fields: [type, status, tags]\n"
        '    warning: "Frontmatter incompleto: faltan {missing_fields}"\n'
        "---\n\n# Reglas\n",
        encoding="utf-8",
    )
    mcp = create_server()
    capture_tool = asyncio.run(mcp.get_tool("inbox.capture"))

    result = capture_tool.fn("Idea rápida", tags="afp, mcp")

    assert "[WARNINGS:" not in result
    files = list(inbox.glob("*.md"))
    assert len(files) == 1
    frontmatter = yaml.safe_load(files[0].read_text(encoding="utf-8").split("---")[1])
    assert frontmatter["type"] == "inbox"
    assert frontmatter["status"] == "captura"
    assert frontmatter["tags"] == ["afp", "mcp"]
    assert str(frontmatter["created"]) == str(frontmatter["updated"])


def test_inbox_capture_ignores_stale_idea_template_frontmatter(tmp_path, monkeypatch):
    vault = _set_vault(monkeypatch, tmp_path)
    inbox = vault / "00_Bandeja"
    inbox.mkdir()
    templates = vault / "Plantillas"
    templates.mkdir()
    (templates / "Idea.md").write_text(
        "---\n"
        "type: apunte\n"
        "status: archivo\n"
        "created: 2020-01-01\n"
        "updated: 2020-01-01\n"
        "---\n\n"
        "# {{title}}\n\n"
        "{{description}}\n",
        encoding="utf-8",
    )
    mcp = create_server()
    capture_tool = asyncio.run(mcp.get_tool("inbox.capture"))

    capture_tool.fn("Idea con plantilla vieja", tags="afp")

    files = list(inbox.glob("*.md"))
    assert len(files) == 1
    frontmatter = yaml.safe_load(files[0].read_text(encoding="utf-8").split("---")[1])
    assert frontmatter["type"] == "inbox"
    assert frontmatter["status"] == "captura"
    assert frontmatter["created"] != "2020-01-01"
    assert frontmatter["updated"] != "2020-01-01"


def test_tag_registry_missing_error_includes_setup_path(tmp_path, monkeypatch):
    _set_vault(monkeypatch, tmp_path)

    result = sync_tag_registry()

    assert not result.success
    assert "04_Recursos/Obsidian/Registro de Tags del Vault.md" in result.error
    assert "Crea" in result.error or "crear" in result.error.lower()


def test_confirmed_write_tools_include_elapsed_time(tmp_path, monkeypatch):
    vault = _set_vault(monkeypatch, tmp_path)
    project = vault / "Project"
    project.mkdir()
    note = project / "scratch.md"
    note.write_text("before target after", encoding="utf-8")
    mcp = create_server()
    apply_tool = asyncio.run(mcp.get_tool("notes.apply_replace"))
    replace_tool = asyncio.run(mcp.get_tool("notes.replace"))
    delete_tool = asyncio.run(mcp.get_tool("notes.delete"))

    apply_result = asyncio.run(
        apply_tool.fn("target", "replacement", _AcceptCtx(), folder="Project")
    )
    replace_result = asyncio.run(
        replace_tool.fn("Project/scratch.md", "# Replaced\n", _AcceptCtx())
    )
    delete_result = asyncio.run(
        delete_tool.fn("Project/scratch.md", _AcceptCtx(), confirm=True)
    )

    assert "Duración:" in apply_result
    assert "Duración:" in replace_result
    assert "Duración:" in delete_result
