import asyncio
import json
from pathlib import Path

from obsidian_mcp.config import reset_settings
from obsidian_mcp.server import create_server
from obsidian_mcp.tools.agents_logic import invalidate_skills_cache
from obsidian_mcp.vault_config import invalidate_vault_config_cache


def test_tool_sets_gate_optional_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    reset_settings()
    invalidate_vault_config_cache()
    invalidate_skills_cache()

    mcp = create_server()
    tool_names = {tool.name for tool in asyncio.run(mcp.list_tools())}

    assert "notes.read" in tool_names
    assert "client.roots" in tool_names
    assert "notes.create" not in tool_names
    assert "vault.stats" not in tool_names
    assert "rag.ask" not in tool_names


def test_tool_set_env_enables_optional_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("OBSIDIAN_MCP_TOOL_SETS", "notes_write,vault_analysis")
    reset_settings()
    invalidate_vault_config_cache()
    invalidate_skills_cache()

    mcp = create_server()
    tool_names = {tool.name for tool in asyncio.run(mcp.list_tools())}

    assert "notes.create" in tool_names
    assert "notes.preview_replace" in tool_names
    assert "vault.stats" in tool_names
    assert "rag.ask" not in tool_names


def test_public_tool_names_are_english(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv(
        "OBSIDIAN_MCP_TOOL_SETS",
        "notes_write,vault_analysis,agents_admin,youtube,canvas,kanvas",
    )
    reset_settings()
    invalidate_vault_config_cache()
    invalidate_skills_cache()

    mcp = create_server()
    tool_names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    forbidden_fragments = [
        "listar",
        "obtener",
        "leer",
        "crear",
        "editar",
        "agregar",
        "buscar",
        "sincronizar",
        "captura",
    ]

    assert not {
        name
        for name in tool_names
        if any(fragment in name for fragment in forbidden_fragments)
    }


def test_write_tool_annotations_are_exposed(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("OBSIDIAN_MCP_TOOL_SETS", "notes_write")
    reset_settings()
    invalidate_vault_config_cache()
    invalidate_skills_cache()

    mcp = create_server()
    create_note = asyncio.run(mcp.get_tool("notes.create"))
    delete_note = asyncio.run(mcp.get_tool("notes.delete"))

    assert create_note.annotations.readOnlyHint is False
    assert create_note.annotations.idempotentHint is False
    assert create_note.meta == {"tool_set": "notes_write"}
    assert delete_note.annotations.destructiveHint is True


def test_mcpb_manifest_contract():
    manifest_path = Path("mcpb/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == "0.4"
    assert manifest["server"]["type"] == "python"
    assert manifest["server"]["mcp_config"]["env"]["OBSIDIAN_VAULT_PATH"]
    assert manifest["user_config"]["vaultPath"]["type"] == "directory"
    assert "toolSets" in manifest["user_config"]
    assert "obsidianRagApiUrl" in manifest["user_config"]


def test_afp_manifest_contract():
    manifest_path = Path("afp.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest == {
        "afp_version": "0.2",
        "subject_uri": "mcp://github.com/Vasallo94/obsidian-mcp-server",
        "sink": {
            "type": "github_issues",
            "repo": "Vasallo94/obsidian-mcp-server",
            "label": "afp-report",
        },
        "redaction": "required",
        "accepts_remote": True,
        "schema_extensions": [],
    }
