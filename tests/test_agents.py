# We verify the tools exist in the module and are decorated correctly.
# These tests mock validate_configuration to avoid requiring a real vault.

from unittest.mock import patch

import pytest

from obsidian_mcp.server import create_server


@pytest.fixture
def mock_valid_vault():
    """Mock configuration validation to allow server creation without a real vault."""
    with patch("obsidian_mcp.server.validate_configuration") as mock_validate:
        mock_validate.return_value = (True, "")
        yield mock_validate


def test_agent_tools_registration(mock_valid_vault):
    """Verify that agent tools are registered in the server."""
    mcp = create_server()
    # FastMCP stores tools in an internal registry.
    tool_names = (
        [t.name for t in mcp._tool_manager._tools.values()]  # type: ignore
        if hasattr(mcp._tool_manager, "_tools")
        else []
    )

    # Fallback for different FastMCP versions
    if not tool_names and hasattr(mcp._tool_manager, "tools"):
        tool_names = [t.name for t in mcp._tool_manager.tools.values()]  # type: ignore

    assert "listar_agentes" in tool_names
    assert "obtener_instrucciones_agente" in tool_names
    assert "obtener_reglas_globales" in tool_names


def test_navigation_move_registration(mock_valid_vault):
    """Verify that mover_nota is registered."""
    mcp = create_server()
    tool_names = [t.name for t in mcp._tool_manager._tools.values()]  # type: ignore
    assert "mover_nota" in tool_names
