"""MCP tool for fetching YouTube transcripts."""

from typing import Optional

from fastmcp import FastMCP

from .registry import register_tool


def register_youtube_tools(mcp: FastMCP) -> None:
    """Register YouTube tools."""

    @register_tool(mcp, "get_youtube_transcript")
    def get_youtube_transcript(url: str, language: Optional[str] = None) -> str:
        """Fetch a YouTube transcript by URL or video ID."""
        from .youtube_logic import get_transcript_text

        return get_transcript_text(url, language).to_display()
