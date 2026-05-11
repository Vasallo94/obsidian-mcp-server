"""Optional public prompt packs."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import get_vault_path
from ..vault_config import get_vault_config


def register_prompt_pack_prompts(mcp: FastMCP) -> None:
    """Register optional public prompt packs enabled by vault config."""
    if "mermaid" not in _enabled_prompt_sets():
        return

    @mcp.prompt(name="create_mermaid_diagram")
    def create_mermaid_diagram(
        subject: str,
        diagram_type: str = "flowchart",
        source_context: str = "",
    ) -> str:
        """
        Create an Obsidian-safe Mermaid diagram.

        Args:
            subject: Topic, system, or process to diagram.
            diagram_type: Mermaid diagram type.
            source_context: Optional source text or code context.
        """
        return f"""
        Create an Obsidian-safe Mermaid {diagram_type} diagram for:
        "{subject}".

        Source context:
        {source_context}

        Requirements:
        1. Use Mermaid syntax that renders reliably in Obsidian.
        2. Avoid parentheses, quotes, HTML, and emojis inside node labels.
        3. Prefer short node labels and move details to edge labels.
        4. Return the diagram in a fenced `mermaid` block.
        5. If the input is ambiguous, make the simplest useful diagram and
           state any assumptions after the block.
        """

    @mcp.prompt(name="fix_obsidian_mermaid")
    def fix_obsidian_mermaid(diagram: str) -> str:
        """
        Fix Mermaid syntax for Obsidian compatibility.

        Args:
            diagram: Mermaid source to repair.
        """
        return f"""
        Repair this Mermaid diagram so it renders in Obsidian:

        ```mermaid
        {diagram}
        ```

        Requirements:
        1. Preserve the diagram's meaning.
        2. Remove syntax that commonly breaks Obsidian Mermaid rendering:
           parentheses in labels, escaped quotes, HTML line breaks, and overly
           complex labels.
        3. Return only a corrected fenced `mermaid` block plus a short note if
           you had to change semantics.
        """


def _enabled_prompt_sets() -> set[str]:
    vault_path = get_vault_path()
    if not vault_path:
        return set()
    config = get_vault_config(vault_path)
    if not config:
        return set()
    return set(config.profile.prompt_sets)
