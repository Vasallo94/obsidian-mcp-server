"""notes.create(note_type=...) elige plantilla y carpeta desde taxonomy.templates."""

import asyncio

import pytest
import yaml

from obsidian_mcp.config import reset_settings
from obsidian_mcp.middleware import invalidate_rules_cache
from obsidian_mcp.server import create_server
from obsidian_mcp.utils import invalidate_note_cache

VAULT_YAML = """\
templates_folder: Plantillas
taxonomy:
  types: [runbook, apunte, inbox]
  templates:
    runbook: {template: Runbook.md, folder: Sistemas}
    apunte: {template: Apunte.md, folder: Conocimiento, choose_subfolder: true}
"""


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    for d in (
        "Plantillas",
        "Sistemas",
        "Conocimiento/IA",
        "Conocimiento/Física",
        ".agents",
    ):
        (v / d).mkdir(parents=True)
    (v / ".agents" / "vault.yaml").write_text(VAULT_YAML, encoding="utf-8")
    (v / "Plantillas" / "Runbook.md").write_text(
        "---\ntitle: '{{title}}'\ntype: runbook\nstatus: en_proceso\n---\n\n## Contexto\n",
        encoding="utf-8",
    )
    (v / "Plantillas" / "Apunte.md").write_text(
        "---\ntitle: '{{title}}'\ntype: apunte\nstatus: en_proceso\n---\n\n## Idea principal\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
    monkeypatch.setenv("OBSIDIAN_MCP_TOOL_SETS", "notes_write,vault_analysis")
    reset_settings()
    invalidate_rules_cache()
    invalidate_note_cache()
    return v


def _tool(name):
    return asyncio.run(create_server().get_tool(name)).fn


def _fm(path):
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])


def test_note_type_picks_template_and_folder(vault):
    result = _tool("notes.create")("Backup del NAS", "", note_type="runbook")

    note = vault / "Sistemas" / "Backup del NAS.md"
    assert note.exists(), result
    assert _fm(note)["type"] == "runbook"
    assert "## Contexto" in note.read_text(encoding="utf-8")


def test_choose_subfolder_requires_folder_and_lists_options(vault):
    result = _tool("notes.create")("Redes neuronales", "", note_type="apunte")

    assert "IA" in result and "Física" in result
    assert not list(vault.rglob("Redes neuronales.md"))


def test_choose_subfolder_with_folder_creates_note(vault):
    _tool("notes.create")(
        "Redes neuronales", "", folder="Conocimiento/IA", note_type="apunte"
    )

    note = vault / "Conocimiento" / "IA" / "Redes neuronales.md"
    assert _fm(note)["type"] == "apunte"
    assert "## Idea principal" in note.read_text(encoding="utf-8")


def test_unknown_note_type_is_rejected(vault):
    result = _tool("notes.create")("X", "", folder="Sistemas", note_type="inventado")

    assert "inventado" in result and "runbook" in result
    assert not (vault / "Sistemas" / "X.md").exists()


def test_valid_type_without_template_sets_type(vault):
    _tool("notes.create")("Idea", "hola", folder="Sistemas", note_type="inbox")

    assert _fm(vault / "Sistemas" / "Idea.md")["type"] == "inbox"


def test_templates_list_shows_mapping(vault):
    result = _tool("templates.list")()

    assert "runbook" in result and "Runbook.md" in result and "Sistemas" in result
