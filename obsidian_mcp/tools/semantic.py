"""Legacy in-process semantic search tools."""

import asyncio
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from ..utils import get_logger
from .registry import enabled_tool_sets, register_tool

logger = get_logger(__name__)


def register_semantic_tools(mcp: FastMCP) -> None:
    """Register legacy semantic tools only when the pack is explicitly enabled."""
    if "legacy_semantic" not in enabled_tool_sets():
        logger.info(
            "Legacy semantic tools omitted. Enable tool set 'legacy_semantic' "
            "or use the ObsidianRAG pack for RAG."
        )
        return

    logger.warning(
        "The 'legacy_semantic' tool set is deprecated. Prefer the 'obsidianrag' "
        "tool set, which delegates semantic search to the external ObsidianRAG service."
    )

    try:
        # pylint: disable-next=import-outside-toplevel,unused-import
        import chromadb  # noqa: F401

        # pylint: disable-next=import-outside-toplevel,unused-import
        import langchain  # noqa: F401

        @register_tool(mcp, "semantic_search")
        async def semantic_search(
            query: str,
            metadata_filter: Optional[Dict[str, Any]] = None,
        ) -> str:
            """Run a semantic vault question through the legacy local RAG stack."""
            from .semantic_logic import ask_knowledge

            try:
                result = ask_knowledge(query, metadata_filter).to_display()
                return _deprecated_result(result)
            except Exception as e:  # pylint: disable=broad-exception-caught
                return f"Error running semantic search: {e}"

        @register_tool(mcp, "index_vault_semantic")
        async def index_vault_semantic(ctx, force: bool = False) -> str:
            """Update the legacy semantic index for the vault."""
            from .semantic_logic import index_semantic_vault

            try:
                await ctx.report_progress(0, 1, "Indexing semantic vault...")
                result = await asyncio.to_thread(index_semantic_vault, force)
                await ctx.report_progress(1, 1, "Semantic indexing complete")
                return _deprecated_result(result.to_display())
            except Exception as e:  # pylint: disable=broad-exception-caught
                return f"Error updating semantic index: {e}"

        @register_tool(mcp, "suggest_semantic_connections")
        async def suggest_semantic_connections(
            threshold: float = 0.70,
            limit: int = 5,
            include_folders: Optional[list[str]] = None,
            exclude_mocs: bool = True,
            min_words: int = 150,
        ) -> str:
            """Find semantically similar notes that are not linked together."""
            from .semantic_logic import find_suggested_connections

            try:
                result = find_suggested_connections(
                    threshold,
                    limit,
                    include_folders,
                    exclude_mocs,
                    min_words,
                ).to_display()
                return _deprecated_result(result)
            except ValueError as e:
                return f"Error finding semantic connections: {e}"

        logger.info("Legacy semantic tools registered")

    except ImportError:
        logger.warning(
            "Legacy semantic tools omitted: install optional RAG dependencies "
            "or use the ObsidianRAG integration."
        )


def _deprecated_result(result: str) -> str:
    """Prefix legacy semantic responses with a migration hint."""
    return (
        "Deprecated: `legacy_semantic` is maintained for backwards compatibility. "
        "Prefer the `obsidianrag` tool set with `rag_health` and `ask_vault`.\n\n"
        f"{result}"
    )
