"""MCP resources for the Obsidian server."""

from fastmcp import FastMCP

from .profile import register_profile_resources
from .vault_info import register_vault_resources as register_vault_info_resources


def register_vault_resources(mcp: FastMCP) -> None:
    """Register all vault-related MCP resources."""
    register_vault_info_resources(mcp)
    register_profile_resources(mcp)


__all__ = [
    "register_vault_resources",
]
