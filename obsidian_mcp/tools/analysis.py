"""MCP vault analysis tools."""

from fastmcp import FastMCP

from .analysis_logic import (
    analyze_links as analyze_links_logic,
)
from .analysis_logic import (
    analyze_tags as analyze_tags_logic,
)
from .analysis_logic import (
    find_broken_wikilinks as find_broken_wikilinks_logic,
)
from .analysis_logic import (
    get_canonical_tags as get_canonical_tags_logic,
)
from .analysis_logic import (
    get_recent_activity,
    list_all_tags,
)
from .analysis_logic import (
    get_vault_stats as get_vault_stats_logic,
)
from .analysis_logic import (
    sync_tag_registry as sync_tag_registry_logic,
)
from .registry import register_tool


def register_analysis_tools(mcp: FastMCP) -> None:
    """Register vault analysis tools."""

    @register_tool(mcp, "get_vault_stats")
    def get_vault_stats() -> str:
        """Generate vault statistics."""
        try:
            return get_vault_stats_logic().to_display()
        except (OSError, ValueError) as e:
            return f"Error generating vault stats: {e}"

    @register_tool(mcp, "get_canonical_tags")
    def get_canonical_tags() -> str:
        """Read the canonical tag registry."""
        try:
            return get_canonical_tags_logic().to_display()
        except (OSError, ValueError) as e:
            return f"Error reading canonical tags: {e}"

    @register_tool(mcp, "analyze_tags")
    def analyze_tags() -> str:
        """Analyze tag usage in the vault."""
        try:
            return analyze_tags_logic().to_display()
        except (OSError, ValueError) as e:
            return f"Error analyzing tags: {e}"

    @register_tool(mcp, "sync_tag_registry")
    def sync_tag_registry(update: bool = False) -> str:
        """Sync vault tag usage with the canonical tag registry."""
        try:
            return sync_tag_registry_logic(update).to_display()
        except (OSError, ValueError) as e:
            return f"Error syncing tag registry: {e}"

    @register_tool(mcp, "list_tags")
    def list_tags() -> str:
        """List all tags currently used in the vault."""
        try:
            return list_all_tags().to_display()
        except (OSError, ValueError) as e:
            return f"Error listing tags: {e}"

    @register_tool(mcp, "analyze_links")
    def analyze_links() -> str:
        """Analyze internal links in the vault.

        High-level overview (counts of broken/valid/most-referenced).
        For per-link broken-with-suggestions output, use
        ``find_broken_wikilinks`` instead.
        """
        try:
            return analyze_links_logic().to_display()
        except (OSError, ValueError) as e:
            return f"Error analyzing links: {e}"

    @register_tool(mcp, "find_broken_wikilinks")
    def find_broken_wikilinks(limit: int = 100) -> str:
        """Find every wikilink in the vault whose target note doesn't exist.

        Issue #6: returns source-file + line + fuzzy suggestions for each
        broken ``[[target]]`` reference, so renames and typos can be
        fixed without manual grepping.

        Args:
            limit: Max number of broken links in the response (default 100).
                0 = no limit.
        """
        try:
            return find_broken_wikilinks_logic(limit=limit).to_display()
        except (OSError, ValueError) as e:
            return f"Error finding broken wikilinks: {e}"

    @register_tool(mcp, "summarize_recent_activity")
    def summarize_recent_activity(days: int = 7) -> str:
        """Summarize recent vault activity."""
        try:
            return get_recent_activity(days).to_display()
        except (OSError, ValueError) as e:
            return f"Error summarizing recent activity: {e}"
