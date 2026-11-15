"""MCP context and routing tools for the active Obsidian vault."""

import json
import warnings
from typing import Any

from fastmcp import Context, FastMCP
from mcp.shared.exceptions import MCPDeprecationWarning

from .context_logic import (
    build_vault_health_report,
    diagnose_vault_setup_report,
    route_task_request,
)
from .context_logic import (
    read_vault_context as read_vault_context_logic,
)
from .registry import register_tool

# roots is deprecated from protocol 2026-07-28 (SEP-2577), whose servers can't
# call the client; older clients still answer. Filtered once, not around the
# await (catch_warnings is process-wide state shared by concurrent calls).
warnings.filterwarnings(
    "ignore", message="The roots capability", category=MCPDeprecationWarning
)


def register_context_tools(mcp: FastMCP) -> None:
    """Register vault context tools."""

    @register_tool(mcp, "vault.context")
    def read_vault_context() -> str:
        """Read the vault structure, templates, and common metadata."""
        try:
            return read_vault_context_logic().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error reading vault context: {e}"

    @register_tool(mcp, "vault.health")
    def health_check() -> str:
        """Validate the active vault and MCP profile configuration."""
        try:
            return build_vault_health_report().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error running health check: {e}"

    @register_tool(mcp, "vault.diagnose")
    def diagnose_vault_setup() -> str:
        """Diagnose vault setup issues and return actionable recommendations."""
        try:
            return diagnose_vault_setup_report().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error diagnosing vault setup: {e}"

    @register_tool(mcp, "client.roots")
    async def list_client_roots(ctx: Context) -> str:
        """List filesystem roots advertised by the connected MCP client."""
        try:
            roots = (await ctx.session.list_roots()).roots
            payload: dict[str, Any] = {
                "supported": True,
                "roots": [
                    {
                        "uri": str(root.uri),
                        "name": getattr(root, "name", None),
                    }
                    for root in roots
                ],
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)
        except Exception as e:  # pylint: disable=broad-exception-caught
            payload = {
                "supported": False,
                "roots": [],
                "error": str(e),
                "hint": (
                    "The connected client may not support MCP roots/list (it is "
                    "gone from protocol 2026-07-28 on), or this tool was executed "
                    "outside an active MCP client session."
                ),
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)

    @register_tool(mcp, "route.task")
    def route_task(request: str) -> str:
        """Recommend prompts, skills, resources, and tools for a task."""
        try:
            return route_task_request(request).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error routing task: {e}"
