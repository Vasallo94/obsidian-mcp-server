# We verify the tools exist in the module and are decorated correctly.
# Ideally we would mock the fastmcp decorator but here we import the
# underlying functions if they were separate. Since they are decorated inside
# `register_agent_tools`, we should actually test the behavior by mocking the
# vault path?
#
# Wait, the tools in `agents.py` are defined INSIDE `register_agent_tools`.
# This makes them hard to import directly for unit testing without calling
# the register function.
# However, FastMCP instances have a way to call tools.

from obsidian_mcp.server import create_server


def test_agent_tools_registration():
    """Verify that agent tools are registered in the server."""
    mcp = create_server()
    # FastMCP stores tools in an internal registry.
    # Accessing private members is not ideal but effective for verification.
    # Looking at introspection: mcp._tool_manager
    tool_names = (
        [t.name for t in mcp._tool_manager._tools.values()]  # type: ignore
        if hasattr(mcp._tool_manager, "_tools")
        else []
    )

    # If _tools is a dict name->tool or list?
    # Let's try to list them safely
    if not tool_names and hasattr(mcp._tool_manager, "tools"):
        tool_names = [t.name for t in mcp._tool_manager.tools.values()]  # type: ignore

    assert "listar_agentes" in tool_names
    assert "obtener_instrucciones_agente" in tool_names
    assert "obtener_reglas_globales" in tool_names


def test_navigation_move_registration():
    """Verify that mover_nota is registered."""
    mcp = create_server()
    # Assuming _tool_manager pattern holds
    tool_names = [t.name for t in mcp._tool_manager._tools.values()]  # type: ignore
    assert "mover_nota" in tool_names
