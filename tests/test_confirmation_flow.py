"""Confirmation gate for destructive write tools.

AFP regression (report afp_98bb01...): destructive writes used ctx.elicit(),
which silently fails on clients that don't advertise the elicitation capability
(e.g. Claude Code). The client auto-declines the elicit request, so the
confirmation gate had no reachable approval path and every overwrite/delete was
rejected with "el usuario rechazo explicitamente la confirmacion" without any
prompt ever shown.

The gate is now a plain ``confirm=True`` argument. The host's own
tool-permission prompt is the human approval surface; the server no longer
depends on the elicitation capability.
"""

import asyncio

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.messages import ERRORS
from obsidian_mcp.middleware import invalidate_rules_cache
from obsidian_mcp.server import create_server
from obsidian_mcp.utils import invalidate_note_cache
from obsidian_mcp.vault_config import invalidate_vault_config_cache


@pytest.fixture(autouse=True)
def _reset_state():
    yield
    reset_settings()
    invalidate_note_cache()
    invalidate_vault_config_cache()
    invalidate_rules_cache()


def _set_vault(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    monkeypatch.setenv(
        "OBSIDIAN_MCP_TOOL_SETS",
        "notes_write,vault_analysis,secundo_selebro,agents_admin",
    )
    reset_settings()
    invalidate_note_cache()
    invalidate_rules_cache()
    return vault


class TestReplaceConfirmGate:
    def test_replace_without_confirm_leaves_note_untouched(self, tmp_path, monkeypatch):
        vault = _set_vault(monkeypatch, tmp_path)
        note = vault / "note.md"
        note.write_text("original content", encoding="utf-8")
        mcp = create_server()
        replace_tool = asyncio.run(mcp.get_tool("notes.replace"))

        result = replace_tool.fn("note.md", "# Replaced\n")

        assert "confirm=True" in result
        assert note.read_text(encoding="utf-8") == "original content"

    def test_replace_with_confirm_overwrites(self, tmp_path, monkeypatch):
        vault = _set_vault(monkeypatch, tmp_path)
        note = vault / "note.md"
        note.write_text("original content", encoding="utf-8")
        mcp = create_server()
        replace_tool = asyncio.run(mcp.get_tool("notes.replace"))

        result = replace_tool.fn("note.md", "# Replaced\n", confirm=True)

        assert "OK" in result
        assert "# Replaced" in note.read_text(encoding="utf-8")

    def test_replace_tool_does_not_require_ctx_parameter(self, tmp_path, monkeypatch):
        """Regression: the broken design injected a Context for elicit()."""
        _set_vault(monkeypatch, tmp_path)
        mcp = create_server()
        replace_tool = asyncio.run(mcp.get_tool("notes.replace"))

        properties = replace_tool.parameters["properties"]
        assert "ctx" not in properties
        assert properties["confirm"]["default"] is False


class TestDeleteConfirmGate:
    def test_delete_without_confirm_keeps_file(self, tmp_path, monkeypatch):
        vault = _set_vault(monkeypatch, tmp_path)
        note = vault / "scratch.md"
        note.write_text("temporary", encoding="utf-8")
        mcp = create_server()
        delete_tool = asyncio.run(mcp.get_tool("notes.delete"))

        result = delete_tool.fn("scratch.md")

        assert "confirm=True" in result
        assert note.exists()

    def test_delete_with_confirm_removes_file(self, tmp_path, monkeypatch):
        vault = _set_vault(monkeypatch, tmp_path)
        note = vault / "scratch.md"
        note.write_text("temporary", encoding="utf-8")
        mcp = create_server()
        delete_tool = asyncio.run(mcp.get_tool("notes.delete"))

        result = delete_tool.fn("scratch.md", confirm=True)

        assert "OK" in result
        assert not note.exists()


class TestApplyReplaceConfirmGate:
    def test_apply_replace_without_confirm_does_not_write(self, tmp_path, monkeypatch):
        vault = _set_vault(monkeypatch, tmp_path)
        note = vault / "note.md"
        note.write_text("before target after", encoding="utf-8")
        mcp = create_server()
        apply_tool = asyncio.run(mcp.get_tool("notes.apply_replace"))

        result = apply_tool.fn("target", "replacement")

        assert "confirm=True" in result
        assert note.read_text(encoding="utf-8") == "before target after"

    def test_apply_replace_with_confirm_writes(self, tmp_path, monkeypatch):
        vault = _set_vault(monkeypatch, tmp_path)
        note = vault / "note.md"
        note.write_text("before target after", encoding="utf-8")
        mcp = create_server()
        apply_tool = asyncio.run(mcp.get_tool("notes.apply_replace"))

        apply_tool.fn("target", "replacement", confirm=True)

        assert "replacement" in note.read_text(encoding="utf-8")


class TestRulesAddConfirmGate:
    def test_rules_add_without_confirm_does_not_write(self, tmp_path, monkeypatch):
        vault = _set_vault(monkeypatch, tmp_path)
        mcp = create_server()
        add_tool = asyncio.run(mcp.get_tool("rules.add"))

        result = add_tool.fn("No hard-wrap markdown")

        assert "confirm=True" in result
        assert not (vault / ".agents" / "REGLAS_GLOBALES.md").exists()

    def test_rules_add_with_confirm_appends(self, tmp_path, monkeypatch):
        vault = _set_vault(monkeypatch, tmp_path)
        mcp = create_server()
        add_tool = asyncio.run(mcp.get_tool("rules.add"))

        result = add_tool.fn("No hard-wrap markdown", confirm=True)

        rules_file = vault / ".agents" / "REGLAS_GLOBALES.md"
        assert rules_file.exists()
        assert "- No hard-wrap markdown" in rules_file.read_text(encoding="utf-8")
        assert "Regla" in result


class TestConfirmMessage:
    def test_confirm_required_message_is_spanish(self):
        """Issue #13: no English in confirmation errors."""
        msg = ERRORS.WRITE_REQUIRES_CONFIRM.lower()
        assert "cancelled" not in msg
        assert "operation" not in msg
        assert "confirm=True" in ERRORS.WRITE_REQUIRES_CONFIRM
