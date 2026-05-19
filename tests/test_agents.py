# We verify the tools exist in the module and are decorated correctly.
# These tests mock validate_configuration to avoid requiring a real vault.

import asyncio
from unittest.mock import patch

import pytest

from obsidian_mcp.server import create_server


@pytest.fixture
def mock_valid_vault():
    """Mock configuration validation to allow server creation without a real vault."""
    with patch("obsidian_mcp.server.validate_configuration") as mock_validate:
        mock_validate.return_value = (True, "")
        yield mock_validate


def _get_tool_names(mcp) -> list[str]:
    """Get registered tool names using the public FastMCP API."""
    tools = asyncio.run(mcp.list_tools())
    return [t.name for t in tools]


def test_agent_tools_registration(mock_valid_vault):
    """Verify that agent tools are registered in the server."""
    mcp = create_server()
    tool_names = _get_tool_names(mcp)
    assert "skills.list" in tool_names
    assert "skills.read" in tool_names
    assert "rules.get" in tool_names


def test_navigation_move_registration(mock_valid_vault):
    """Verify that move_note is registered when notes_write is enabled."""
    mcp = create_server()
    tool_names = _get_tool_names(mcp)
    assert "notes.move" in tool_names
