"""Main MCP server for Obsidian vault access."""

import sys
from typing import Any, Dict, Literal, Optional

from fastmcp import FastMCP

from .canvas.canvas_tools import register_canvas_tools
from .canvas.workflow_tools import register_workflow_tools
from .config import APP_NAME, validate_configuration
from .prompts import register_assistant_prompts
from .resources import register_vault_resources
from .tools import (
    register_agent_tools,
    register_analysis_tools,
    register_context_tools,
    register_creation_tools,
    register_graph_tools,
    register_navigation_tools,
    register_obsidianrag_tools,
    register_semantic_tools,
    register_youtube_tools,
)
from .utils import get_logger

# Type alias for supported transport protocols
TransportType = Literal["stdio", "http", "sse"]

logger = get_logger(__name__)


def create_server() -> FastMCP:
    """Create and configure the Obsidian MCP server."""
    is_valid, error_message = validate_configuration()
    if not is_valid:
        logger.error(error_message)
        raise ValueError(error_message)

    mcp = FastMCP(APP_NAME)

    logger.info("Registering navigation tools...")
    register_navigation_tools(mcp)

    logger.info("Registering creation tools...")
    register_creation_tools(mcp)

    logger.info("Registering analysis tools...")
    register_analysis_tools(mcp)

    logger.info("Registering graph tools...")
    register_graph_tools(mcp)

    logger.info("Registering YouTube tools...")
    register_youtube_tools(mcp)

    logger.info("Registering context tools...")
    register_context_tools(mcp)

    logger.info("Registering skill tools...")
    register_agent_tools(mcp)

    logger.info("Registering legacy semantic tools...")
    register_semantic_tools(mcp)

    logger.info("Registering ObsidianRAG tools...")
    register_obsidianrag_tools(mcp)

    logger.info("Registering canvas tools...")
    register_canvas_tools(mcp)

    logger.info("Registering Kanvas workflow tools...")
    register_workflow_tools(mcp)

    logger.info("Registering vault resources...")
    register_vault_resources(mcp)

    logger.info("Registering assistant prompts...")
    register_assistant_prompts(mcp)

    logger.info("MCP server configured successfully")
    return mcp


def run_server(
    transport: TransportType = "stdio",
    host: Optional[str] = None,
    port: Optional[int] = None,
    path: Optional[str] = None,
) -> None:
    """Run the MCP server."""
    try:
        logger.info("Starting MCP server", extra={"transport": transport})

        mcp = create_server()

        if transport == "stdio":
            mcp.run()
        elif transport == "http":
            kwargs: Dict[str, Any] = {}
            if host:
                kwargs["host"] = host
            if port:
                kwargs["port"] = str(port)
            if path:
                kwargs["path"] = path
            # FastMCP.run() transport param typing is incomplete
            mcp.run(transport="http", **kwargs)
        elif transport == "sse":
            kwargs_sse: Dict[str, Any] = {}
            if host:
                kwargs_sse["host"] = host
            if port:
                kwargs_sse["port"] = str(port)
            # FastMCP.run() transport param typing is incomplete
            mcp.run(transport="sse", **kwargs_sse)
        else:
            raise ValueError(f"Unsupported transport: {transport}")

        logger.info("Server ready. Waiting for connections...")

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Fatal server error", extra={"error": str(e)})
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Run the default stdio server."""
    run_server()


if __name__ == "__main__":
    main()
