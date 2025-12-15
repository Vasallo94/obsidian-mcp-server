"""
Herramientas MCP para el servidor de Obsidian
"""

from .agents import register_agent_tools
from .analysis import register_analysis_tools
from .context import register_context_tools
from .creation import register_creation_tools
from .navigation import register_navigation_tools
from .youtube import register_youtube_tools

__all__ = [
    "register_analysis_tools",
    "register_creation_tools",
    "register_navigation_tools",
    "register_youtube_tools",
    "register_context_tools",
    "register_agent_tools",
]
