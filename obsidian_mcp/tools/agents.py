"""MCP tools and resources for vault skills."""

from __future__ import annotations

from fastmcp import FastMCP

from .agents_generator import generate_skill, suggest_skills_for_vault, sync_skills
from .agents_logic import (
    get_agent_instructions,
    list_available_skills,
    validate_note_logic,
)
from .agents_logic import (
    get_global_rules as get_global_rules_logic,
)
from .agents_logic import (
    refresh_skills_cache as refresh_skills_cache_logic,
)
from .registry import register_tool


def register_agent_tools(mcp: FastMCP) -> None:
    """Register vault skill tools and resources."""

    @register_tool(mcp, "list_skills")
    def list_skills() -> str:
        """List skills available in the vault."""
        return list_available_skills().to_display()

    @register_tool(mcp, "read_skill")
    def read_skill(name: str) -> str:
        """Read a specific vault skill file."""
        return get_agent_instructions(name).to_display()

    @register_tool(mcp, "get_global_rules")
    def get_global_rules() -> str:
        """Read global vault agent rules."""
        return get_global_rules_logic().to_display()

    @register_tool(mcp, "validate_note")
    def validate_note(
        content: str,
        title: str = "",
        mode: str = "create",
    ) -> str:
        """Lint a note against vault rules without writing it.

        Use BEFORE create_note / patch_note to surface frontmatter, heading,
        and tag violations in-context. Cheaper than round-tripping a write.

        Args:
            content: Full note body (YAML frontmatter optional but recommended).
            title: Optional note title for rules with scope='title'.
            mode: 'create' (default), 'edit', or 'append'.
        """
        return validate_note_logic(title=title, content=content, mode=mode).to_display()

    @register_tool(mcp, "refresh_skills_cache")
    def refresh_skills_cache() -> str:
        """Invalidate and refresh the in-memory skill cache."""
        return refresh_skills_cache_logic().to_display()

    @register_tool(mcp, "create_skill")
    def create_skill(
        name: str,
        description: str,
        instructions: str,
        tools: str = "",
        default_location: str = "",
    ) -> str:
        """Generate a new vault skill with a consistent structure."""
        return generate_skill(
            name,
            description,
            instructions,
            tools,
            default_location,
        ).to_display()

    @register_tool(mcp, "suggest_vault_skills")
    def suggest_vault_skills() -> str:
        """Analyze the vault and suggest useful personal skills."""
        return suggest_skills_for_vault().to_display()

    @register_tool(mcp, "sync_skills")
    def sync_vault_skills(update: bool = False) -> str:
        """Validate skills and optionally apply automatic fixes."""
        return sync_skills(update).to_display()
