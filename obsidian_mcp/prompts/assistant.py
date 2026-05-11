"""Prompt registry for the Obsidian MCP server."""

from fastmcp import FastMCP

from .core import register_core_prompts
from .packs import register_prompt_pack_prompts
from .profiles import register_profile_prompts


def register_assistant_prompts(mcp: FastMCP) -> None:
    """Register core, optional pack, and vault-profile prompts."""
    register_core_prompts(mcp)
    register_prompt_pack_prompts(mcp)
    register_profile_prompts(mcp)
