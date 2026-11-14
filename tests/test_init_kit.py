"""vault.init_kit copia el kit base solo donde falta."""

import asyncio

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.middleware import invalidate_rules_cache
from obsidian_mcp.server import create_server
from obsidian_mcp.tools.agents_logic import KIT_DIR


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    v.mkdir()
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
    monkeypatch.setenv("OBSIDIAN_MCP_TOOL_SETS", "agents_admin,notes_write")
    reset_settings()
    invalidate_rules_cache()
    return v


def _tool(name):
    return asyncio.run(create_server().get_tool(name)).fn


def test_preview_writes_nothing(vault):
    result = _tool("vault.init_kit")()

    assert "Se crearían" in result and "Plantillas/Runbook.md" in result
    assert not list(vault.iterdir())


def test_confirm_creates_kit_and_rules_are_active(vault):
    _tool("vault.init_kit")(confirm=True)

    assert (vault / ".agents" / "REGLAS_GLOBALES.md").exists()
    assert (vault / "AGENTS.md").exists()
    assert len(list((vault / "Plantillas").glob("*.md"))) == len(
        list((KIT_DIR / "templates").glob("*.md"))
    )
    assert "Frontmatter incompleto" in _tool("notes.validate")("# Hola", title="Hola")


def test_existing_files_are_never_overwritten(vault):
    (vault / "AGENTS.md").write_text("mío", encoding="utf-8")
    (vault / "Templates").mkdir()
    (vault / "Templates" / "Runbook.md").write_text("mío", encoding="utf-8")

    result = _tool("vault.init_kit")(confirm=True)

    assert (vault / "AGENTS.md").read_text(encoding="utf-8") == "mío"
    assert (vault / "Templates" / "Runbook.md").read_text(encoding="utf-8") == "mío"
    assert (vault / "Templates" / "Apunte.md").exists()  # detected folder reused
    assert not (vault / "Plantillas").exists()
    assert "Ya existían" in result


def test_configured_templates_folder_is_used(vault):
    (vault / ".agents").mkdir()
    (vault / ".agents" / "vault.yaml").write_text(
        'templates_folder: "ZZ"\n', encoding="utf-8"
    )

    _tool("vault.init_kit")(confirm=True)

    assert (vault / "ZZ" / "Idea.md").exists()


def test_symlinked_folder_outside_vault_is_refused(vault, tmp_path):
    outside = tmp_path / "fuera"
    outside.mkdir()
    (vault / "Plantillas").symlink_to(outside)

    result = _tool("vault.init_kit")(confirm=True)

    assert "fuera del vault" in result
    assert not list(outside.iterdir())


def test_kit_templates_use_placeholders_not_fixed_dates():
    for template in (KIT_DIR / "templates").glob("*.md"):
        text = template.read_text(encoding="utf-8")
        assert "{{title}}" in text and "{{date}}" in text, template.name
        assert "2026-" not in text, template.name
